import pandas as pd
import numpy as np

def load_processed(path):
    # parquet読込
    df = pd.read_parquet(path)
    return df

def add_gc_rate(df):
    # gc累積 → レート
    df = df.copy()
    elapsed = df['timestamp'].diff().dt.total_seconds()

    df['gc_count_rate'] = df['gc_count_total'].diff() / elapsed
    df.loc[df["gc_count_rate"] < 0, "gc_count_rate"] = np.nan

    df['gc_time_rate_ms'] = df['gc_time_ms_total'].diff() / elapsed
    df.loc[df["gc_time_rate_ms"] < 0, "gc_time_rate_ms"] = np.nan

    return df

def main():
    path = "data/processed/server_metrics_20260504.parquet"
    df = load_processed(path)
    df = add_gc_rate(df)
    df = df.dropna()
    print(df)

if __name__ == '__main__':
    main()
