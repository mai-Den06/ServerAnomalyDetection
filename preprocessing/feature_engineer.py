def load_processed(path):
    # parquet読込
    pass

def add_gc_rate(df):
    # gc累積 → レート
    pass

def main():
    path = "data/processed/server_metrics_20260504.parquet"
    df = load_processed(path)
    df = add_gc_rate(df)

if __name__ == '__main__':
    main()
