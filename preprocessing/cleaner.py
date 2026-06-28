from pathlib import Path
import pandas as pd

def load_raw(path):
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    return df

def resample_session(df):
    # timestampをindex化し5秒グリッドへ
    df = df.set_index('timestamp')
    df = df.resample("5s").mean()
    return df

def save_processed(df, path):
    # `data/processed/` にParquet保存
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)

def main():
    df03 = load_raw("data/raw/server_metrics_20260503.csv")
    df04 = load_raw("data/raw/server_metrics_20260504.csv")
    df = pd.concat([df03, df04]).sort_values("timestamp")
    # df = resample_session(df) # 多変量 IF/LOF は時間軸を見ないため影響がほぼないためスキップ
    save_processed(df, "data/processed/server_metrics_20260503_20260504.parquet")

if __name__ == '__main__':
    main()
