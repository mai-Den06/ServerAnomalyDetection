# Isolation Forest 設計プラン

モデル構築フェーズ最初の手法として Isolation Forest（IF）を実装するための設計メモ。
手法順は `IF → PCA再構成 → window PCA`、評価は正解ラベル不在のため `3σ閾値＋偏離度` を共通指標とする方針。

## 1. 前提（EDAで確定したこと）

- データ: `data/processed/server_metrics_20260503_20260504.parquet`（03+04結合・2647行）
- `mspt`: avg/min は強相関、**max は独立** → スパイク型異常の信号は `max` に集約される
- `tps` は平坦で除去済み → **正解ラベルでの評価は不可**
- `online_players` と `mspt` は負相関。活動期/アイドル期で挙動が二相
- 準定数で稀に跳ねる列が複数（`cpu_process_pct` / `gc_count_rate` / `gc_time_rate_ms` / `thread_count`）
  → スパイク検知の主力軸になりうる一方、異常方向を支配しすぎないか要確認

## 2. 入力データ — 最初の判断

**IsolationForest はスケール不変**（各特徴で独立にランダム分割するため、標準化しても木の分割位置は実質変わらない）。
したがって EDA で作った標準化済み `X` を使う必要はない。

→ **標準化の手前の `df`** を入力にする（rate化・累積/定数列の除去・`dropna` 済み）。

理由:
- スコア解釈時に元スケールの値（例: `mspt_5s_max` の生mspt）と突き合わせやすい
- 標準化Xを挟むと IF には不要な工程がパイプラインに残り、後続手法と混乱する

具体的には `notebooks/01_data_exploration.ipynb` の `scaler.fit_transform` 直前の `df` を入力に使う。

## 3. モデルパラメータの考え方

| パラメータ | 方針 |
|---|---|
| `n_estimators` | 200〜300（2647行なら十分。デフォルト100でも可） |
| `max_samples` | `'auto'`（256）。データが少ないので `min(256, n)` で問題なし |
| `contamination` | **`'auto'` で開始**。正解ラベルが無い以上、固定値を先に決め打ちしない。score分布を見てから閾値を引く |
| `random_state` | 固定（再現性確保） |

## 4. スコアと閾値 — 共通指標への接続

- `score_samples(df)`（高いほど正常）または `-decision_function(df)`（高いほど異常）で anomaly score を取得
- tps平坦で正解が無いため、IFスコアを単独で 3σ判定にかけるのではなく、まず **スコア分布の形**（二峰性・裾の厚み）を見る
- 評価の軸は **IFの異常順位 と 3σ偏離度 の重なり**を見ること

## 5. 検証チェックポイント（"動いた" の確認材料）

1. score分布のヒストグラム（二峰性が出るか／裾の厚み）
2. 上位異常 N点を `df` の元値で表示 → **`mspt_*_max` が大きい点が上位に来るか**（EDAの「スパイクはmaxに集約」と整合するか）
3. 時系列プロットに異常点を重ねる（01 のトレンド図に散布を追加）
4. 準定数列（`cpu_process_pct` / `gc_*_rate` / `thread_count`）の跳ねが異常判定を支配していないか確認
   → 支配的なら特徴量セットを見直す材料にする

## 6. 成果物の置き場所

- **探索は新規 notebook**（README想定名 `notebooks/03_ml_methods.ipynb`）で進める
- 挙動が固まったら `detectors/ml/isolation_forest.py` に共通I/Fで落とす
- 上記2段にすると手戻りが少ない

## 7. 次の手法への接続

IF で得た「異常スコア＋上位異常点」は、後続の PCA再構成誤差・window PCA と **同じ評価土俵（3σ＋偏離度との重なり）** で比較する。
そのため共通評価（`evaluation/`）と detector の共通I/F（`detectors/base_detector.py`）を、IF が固まった段階で先に決めておくと比較がスムーズ。

---

作業ブランチ: `feature-isolation-forest`（develop から作成）。
