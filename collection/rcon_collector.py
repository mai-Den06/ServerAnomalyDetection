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

            response = mcr.command("/list")
            match = re.search(r'There are (\d+)', response)
            online_players = int(match.group(1))

    now = datetime.now().replace(microsecond=0)
    df = pd.DataFrame({
        "timestamp": [now],
        "tps": [tps],
        "online_players": [online_players]
    })

    return df

def loop(dry_run):
    interval = settings["collection"]["interval_seconds"]
    while (True):
        today = datetime.now().strftime("%Y%m%d")
        dir_path = Path(settings["paths"]["raw_data"])
        file_path = dir_path / f"tps_{today}.csv"
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
