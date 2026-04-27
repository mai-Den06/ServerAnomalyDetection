import os
import re
import time
from datetime import datetime
from pathlib import Path
import argparse
from dotenv import load_dotenv
import yaml
from mcrcon import MCRcon
import pandas as pd

load_dotenv()
HOST = os.getenv("RCON_HOST")
PORT = int(os.getenv("RCON_PORT"))
PASSWORD = os.getenv("RCON_PASSWORD")

with open("config/settings.yaml") as f:
    settings = yaml.safe_load(f)

def parse_mspt(raw: str) -> dict:
    clean = re.sub(r'§.', '', raw)
    groups = re.findall(r'([\d.]+)/([\d.]+)/([\d.]+)', clean)
    labels = ['5s', '10s', '1m']
    return {
        labels[i]: {
            'avg': float(groups[i][0]),
            'min': float(groups[i][1]),
            'max': float(groups[i][2]),
        }
        for i in range(3)
    }

def read(dry_run):
    if dry_run:
        tps = 20.0
        online_players = 0
    else:
        with MCRcon(HOST, PASSWORD, port=PORT) as mcr:
            response = mcr.command("/tps")
            cleaned = re.sub(r'§.', '', response)
            values = re.findall(r'[\d.]+', cleaned)
            tps = float(values[3])

            response = mcr.command("/mspt")
            mspt = parse_mspt(response)
            flat_mspt = {
                f"mspt_{window}_{stat}": val
                for window, stats in mspt.items()
                for stat, val in stats.items()
            }

            response = mcr.command("/list")
            match = re.search(r'There are (\d+)', response)
            online_players = int(match.group(1))

    now = datetime.now().replace(microsecond=0)
    df = pd.DataFrame([{
        "timestamp": now,
        "tps": tps,
        **flat_mspt,
        "online_players": online_players
    }])

    return df

def wait_for_rcon(dry_run):
    if dry_run:
        return
    max_retries = settings["startup"]["max_retries"]
    interval = settings["startup"]["retry_interval"]
    for attempt in range(1, max_retries + 1):
        try:
            with MCRcon(HOST, PASSWORD, port=PORT) as mcr:
                mcr.command("/list")
            print(f"RCON接続成功（試行 {attempt} 回目）")
            return
        except Exception as e:
            print(f"RCON待機中... ({attempt}/{max_retries}): {e}")
            time.sleep(interval)
    raise RuntimeError(f"RCON接続失敗: {max_retries}回リトライしても接続できませんでした")

def loop(dry_run):
    wait_for_rcon(dry_run)
    interval = settings["collection"]["interval_seconds"]
    while (True):
        today = datetime.now().strftime("%Y%m%d")
        dir_path = Path(settings["paths"]["raw_data"])
        file_path = dir_path / f"server_metrics_{today}.csv"
        dir_path.mkdir(parents=True, exist_ok=True)

        df = read(dry_run)
        df.to_csv(file_path, mode="a", header=not file_path.exists(), index=False)
        time.sleep(interval)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    loop(args.dry_run)

if __name__ == '__main__':
    main()
