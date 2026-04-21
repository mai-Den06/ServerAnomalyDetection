# ServerAnomalyDetection

Minecraftサーバーの TPS（Ticks Per Second）時系列データを用いた教師なし異常検知の実装・比較プロジェクト。

統計的手法から機械学習まで複数のアプローチを実装し、手法間の特性を比較することで、実務での時系列異常検知に活かせる知見を積むことを目的とする。

## 概要

Minecraft サーバーは毎秒 20 回のゲームティックを処理する。この TPS が低下するとサーバーラグが発生し、プレイヤー体験が悪化する。TPS は「正常値 = 20.0」という明確な基準を持つため、異常検知の学習データとして扱いやすい。

| 異常パターン | 原因例 | TPS の挙動 |
|---|---|---|
| スパイク型 | TNT 爆発、大量アイテム生成 | 一時的急落 → 即回復 |
| 持続型 | チャンク過多読み込み、MOB 蓄積 | 低水準で継続 |
| 周期型 | 自動ファームの収穫タイミング | 定期的な低下 |
| クリープ型 | メモリリーク、エンティティ蓄積 | 徐々に低下 |

## 実装する異常検知手法

**統計的手法**
- Z-score（グローバル / ローリング）
- 移動平均 ± 3σ（Bollinger Band 的アプローチ）
- STL 分解 + 残差の MAD ベース外れ値検出

**機械学習**
- Isolation Forest
- LOF（Local Outlier Factor）

## プロジェクト構成

```
ServerAnomalyDetection/
├── config/
│   └── settings.yaml               # 接続設定・検知パラメータ
├── collection/
│   ├── spark_api_collector.py      # Spark Web API 経由での TPS 収集
│   └── rcon_collector.py           # RCON 経由（フォールバック）
├── data/
│   ├── raw/                        # 生 CSV（tps_YYYYMMDD.csv）
│   ├── processed/                  # 前処理済み（Parquet）
│   └── labeled/
│       └── anomaly_events.csv      # 意図的ラグのイベントログ
├── preprocessing/
│   ├── cleaner.py                  # 欠損・アーティファクト処理
│   └── feature_engineer.py         # ML 向け特徴量生成
├── detectors/
│   ├── base_detector.py            # 共通インターフェース
│   ├── statistical/
│   │   ├── zscore_detector.py
│   │   ├── moving_avg_detector.py
│   │   └── stl_detector.py
│   └── ml/
│       ├── isolation_forest.py
│       └── lof_detector.py
├── evaluation/
│   ├── metrics.py                  # 教師なし評価指標
│   └── comparator.py               # 手法間比較
└── notebooks/
    ├── 01_data_exploration.ipynb
    ├── 02_statistical_methods.ipynb
    ├── 03_ml_methods.ipynb
    ├── 04_comparison.ipynb
    └── 05_simulation_study.ipynb   # 合成データによる手法検証
```

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. Minecraft サーバーの準備

PaperMC サーバーを使用する。`server.properties` で RCON を有効化する。

```properties
enable-rcon=true
rcon.port=25575
rcon.password=<ランダムな文字列>
```

Spark Web API を使用する場合は [Spark プラグイン](https://spark.lucko.me/) を導入する。

### 3. 環境変数の設定

```bash
cp .env.example .env
# .env を編集して接続情報を記入
```

### 4. データ収集の開始

```bash
python -m collection.spark_api_collector   # Spark Web API 使用時
python -m collection.rcon_collector        # RCON 使用時
```

## Ground Truth の確保戦略

教師ラベルがないリアルデータに対して、以下の 3 段階で対処する。

1. **意図的なラグ注入** — TNT 大量爆発・MOB 大量生成などで TPS 低下を再現し、`anomaly_events.csv` に記録して部分的な正解ラベルとして使う
2. **合成データ検証** — 既知のパターンで異常を埋め込んだ合成時系列で Precision / Recall / F1 を計算（`notebooks/05_simulation_study.ipynb`）
3. **教師なし評価指標** — 複数手法のアンサンブル合意率や異常点の時系列パターン分析

## 技術的な注意事項

- TPS の物理上限は 20.0 のため分布が歪む。Z-score の閾値は 3.5〜4.0 程度に緩めること
- プレイヤー 0 人の時間帯は Idle 状態で TPS = 20.0 固定になる。`online_players` を特徴量に含めること
- STL 分解は最低 2 周期分（日次周期なら 2 日分）のデータが揃ってから実行する
- RCON 経由で `/spark tps` を実行すると空レスポンスになるケースがある（[spark issue #119](https://github.com/lucko/spark/issues/119)）。PaperMC 組み込みの `/tps` の方が安定

## 参考

- [Spark — Minecraft performance profiler](https://spark.lucko.me/)
- [Numenta Anomaly Benchmark (NAB)](https://github.com/numenta/NAB)
- [statsmodels STL decomposition](https://www.statsmodels.org/stable/generated/statsmodels.tsa.seasonal.STL.html)
