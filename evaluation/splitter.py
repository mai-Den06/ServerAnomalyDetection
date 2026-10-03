def time_split(df, train_ratio=0.7):
    split = int(len(df) * train_ratio)
    return df.iloc[:split], df.iloc[split:]
