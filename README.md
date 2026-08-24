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

## 詰まった箇所
- データ収集: `collection/rcon_collector.py`
    - mspt出力のparse
- 前処理: `preprocessing/cleaner.py`
    - pandasでのdf操作
    - データ収集時の時間差(5~6秒)により、リサンプル時に空スロットが生まれてしまった
- 標準化: `notebooks/01_data_exploration.ipynb`
    - データセットにより残るカラムが変わってしまう
        - `nunique`の場合、監視中止時の値で意図通り弾けないカラムがあった
        - `std`の場合、外れ値の値によっては弾けないカラムがあった
    - 列の性質はセッションで変わる
    - 上記手段は調査時に使用してカラムを選定し、運用時は固定する

### Claude関連
- claudeによるメモリ改ざん
    - ペアプログラミングで行っている都合上、セッションの切り替えを渋っていたら指示に関わらず、claudeの提案したことを勝手に実行、メモリの改ざん(勝手な書き換え、存在しない記憶の持ち出し)を行ってしまった
        - と言っても`/Context`を確認したが全体の1割程度しか使用していなかった
        - モデルは`Opus 4.8`、Effortは`High`、Thinkingはオン
    - そこで切り替えればよかったが、試しに訂正を繰り返していたら弁明をはじめ、脈絡もなくそれとはわかりづらい形で責任を押し付けてきた
    - 今回の挙動は少しずつといった変化ではなく唐突に変わってしまった
- claudeによるPI誤検知
    - 「PostToolUseフックが`UpdatedToolOutput`でツール結果を差し替えている」という供述
    - `.jsonl`の調査結果、錯覚・作話であったと思われる
- claudeの無意味な単語の連投
    - 原因不明
- claudeの出力放棄
    - thinkingブロックで停止し、出力すべきtextブロックまでたどり着いていない
    - 必ず効くわけではないが「思考過程の出力」を指示することで改善

## 知ったこと
- CSVからParquetにすることで型を保持しながら読み書きを高速化できる
- EDA（Exploratory Data Analysis：探索的データ分析）でデータの特性・構造・傾向を可視化や統計処理を用いて把握し、重要な洞察を得る

|種類|操作|式|結果|
|---|---|---|---|
|正規化|範囲を [0,1]/[-1,1]に収める|(x-min)/(max-min)|範囲固定|
|標準化|mean=0, std=1 にする|(x-mean)/std|平均0, 分散1|
