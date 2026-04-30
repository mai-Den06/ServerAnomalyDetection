import os
import re
import time
from datetime import datetime
from pathlib import Path
import argparse
from dotenv import load_dotenv
import yaml
from mcrcon import MCRcon
from jmxquery import JMXConnection, JMXQuery
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

def read_jmx() -> dict:
    conn = JMXConnection("service:jmx:rmi:///jndi/rmi://localhost:9999/jmxrmi")
    queries = [
        JMXQuery("java.lang:type=Memory", "HeapMemoryUsage"),
        JMXQuery("java.lang:type=Memory", "NonHeapMemoryUsage"),
        JMXQuery("java.lang:type=GarbageCollector,name=*", "CollectionCount"),
        JMXQuery("java.lang:type=GarbageCollector,name=*", "CollectionTime"),
        JMXQuery("java.lang:type=OperatingSystem", "ProcessCpuLoad"),
        JMXQuery("java.lang:type=Threading", "ThreadCount"),
    ]
    results = conn.query(queries)

    heap, non_heap = {}, {}
    gc_count, gc_time = 0, 0
    cpu_load, thread_count = 0, 0
    for r in results:
        if r.attribute == "HeapMemoryUsage" and r.attributeKey in ("used", "max"):
            heap[r.attributeKey] = r.value
        elif r.attribute == "NonHeapMemoryUsage" and r.attributeKey in ("used", "max"):
            non_heap[r.attributeKey] = r.value
        elif r.attribute == "CollectionCount":
            gc_count += r.value
        elif r.attribute == "CollectionTime":
            gc_time += r.value
        elif r.attribute == "ProcessCpuLoad":
            cpu_load += r.value
        elif r.attribute == "ThreadCount":
            thread_count += r.value

    return {
        "heap_used_mb": heap.get("used", 0) / 1024**2,
        "heap_max_mb" : heap.get("max" , 0) / 1024**2,
        "non_heap_used_mb": non_heap.get("used", 0) / 1024**2,
        "gc_count_total": gc_count,
        "gc_time_ms_total": gc_time,
        "cpu_process_pct": cpu_load * 100,
        "thread_count": thread_count,
    }

def read(dry_run, timeout):
    if dry_run:
        tps = 20.0
        dummy_response = "0.0/0.0/0.0, 0.0/0.0/0.0, 0.0/0.0/0.0"
        dummy_mspt = parse_mspt(dummy_response)
        flat_mspt = {
            f"mspt_{window}_{stat}": val
            for window, stats in dummy_mspt.items()
            for stat, val in stats.items()
        }
        jmx = {
            "heap_used_mb": 0.0, "heap_max_mb" : 0.0, "non_heap_used_mb": 0.0,
            "gc_count_total": 0, "gc_time_ms_total": 0,
            "cpu_process_pct": 0.0, "thread_count": 0,
        }
        online_players = 0
    else:
        with MCRcon(HOST, PASSWORD, port=PORT, timeout=timeout) as mcr:
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

        jmx = read_jmx()

    now = datetime.now().replace(microsecond=0)
    df = pd.DataFrame([{
        "timestamp": now,
        "tps": tps,
        **flat_mspt,
        **jmx,
        "online_players": online_players
    }])

    return df

def wait_for_rcon(dry_run, timeout):
    if dry_run:
        return
    max_retries = settings["startup"]["max_retries"]
    interval = settings["startup"]["retry_interval"]
    for attempt in range(1, max_retries + 1):
        try:
            with MCRcon(HOST, PASSWORD, port=PORT, timeout=timeout) as mcr:
                mcr.command("/list")
            print(f"RCON接続成功（試行 {attempt} 回目）")
            return
        except Exception as e:
            print(f"RCON待機中... ({attempt}/{max_retries}): {e}")
            time.sleep(interval)
    raise RuntimeError(f"RCON接続失敗: {max_retries}回リトライしても接続できませんでした")

def loop(dry_run):
    timeout = settings["collection"]["timeout_seconds"]
    wait_for_rcon(dry_run, timeout)
    interval = settings["collection"]["interval_seconds"]
    while (True):
        today = datetime.now().strftime("%Y%m%d")
        dir_path = Path(settings["paths"]["raw_data"])
        file_path = dir_path / f"server_metrics_{today}.csv"
        dir_path.mkdir(parents=True, exist_ok=True)

        df = read(dry_run, timeout)
        df.to_csv(file_path, mode="a", header=not file_path.exists(), index=False)
        time.sleep(interval)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    loop(args.dry_run)

if __name__ == '__main__':
    main()
