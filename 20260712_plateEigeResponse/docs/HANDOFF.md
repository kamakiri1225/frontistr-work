# 引き継ぎログ (HANDOFF) — plate 固有値解析 → 周波数応答解析

最終更新: 2026-07-12 / 作業環境: WSL2 + FrontISTR 5.9

このプロジェクトは、片持ち平板(plate)の **固有値解析** と **周波数応答解析** を FrontISTR で行い、
ブログ記事(docs)にまとめるもの。以下は現状と、続きを行うための情報。

---

## 1. プロジェクトの目的

- easyIstr サンプル `plate.unv` を使い、片持ち板の固有値解析＋周波数応答解析を行う。
- 固有値解析は梁理論と比較して考察（ブログ記事化 → 済）。
- 周波数応答は固有値解析の結果を参照し、コンプライアンス波形をグラフ化（→ 済）。
- easyIstr操作マニュアル(easyistr-3.56.260130)の 4-4-2 節に沿った設定。

## 2. フォルダ構成

```
20260712_plateEigeResponse/
  unv/plate.unv              元メッシュ（easyIstrサンプルからコピー）
  001_eigen/                 Step1: 固有値解析（完了）
    FistrModel.msh           変換済みメッシュ（Steel材料埋め込み、mm-kg-s）
    FistrModel.cnt           固有値解析の制御ファイル
    hecmw_ctrl.dat
    FistrModel.res.0.1..20   固有ベクトル（20モード）
    0.log                    固有値（周波数）一覧 ← 周波数応答が参照
    docs/                    固有値解析のブログ
      20260712_1_FrontISTR固有値解析_梁理論との比較.md / .html
      img/
  002_freqResponse/          Step2: 周波数応答解析（完了）
    FistrModel.cnt           周波数応答の制御ファイル
    hecmw_ctrl.dat           ../001_eigen のメッシュ・固有値結果を参照
    graph.ipynb              コンプライアンス波形の描画ノートブック
    0.log                    周波数-応答振幅の一覧
    docs/
      compliance.csv         周波数-応答データ
      img/compliance.png     コンプライアンス波形グラフ
      （周波数応答のブログ記事は未作成 ← TODO）
  docs/
    WORK_LOG.md              作業メモ
    HANDOFF.md               このファイル
    002_freqResponse_001_eigen_reference.md
                             002が001の固有値解析結果を参照する仕組みの解説
```

## 3. 実行環境（重要）

- **FrontISTR ソルバー**: `~/local/frontistr/bin/fistr1`（PATHに無い。フルパスで呼ぶ）
  - build: 5.9, MPI無効, OpenMP有効, --with-lapack
- **UNV→msh 変換**: easyIstr同梱 `unv2fistrEx.py` を **専用Windows Python** で実行する。
  - Linuxの `python3` では必要モジュール(VTK等)が無く失敗する。
  - 専用Python: `/mnt/c/DEXCS/easyIstrPython/Python-3.12.9_withGiVtkSpGm/bin/python3.12.exe`（Windows exe, WSLから起動可）
  - 必要な環境変数（Windowsパス）を WSLENV 経由で渡す。

### メッシュ変換コマンド（再現用）
```bash
cd 001_eigen
export easyIstrPath='C:\DEXCS\easyIstrPython\easyIstr'
export easyIstrUserPath='D:\work\easyIstrUser'
export PYTHONPATH='C:\DEXCS\easyIstrPython\easyIstr\python;C:\DEXCS\easyIstrPython\easyIstr\bin'
export WSLENV=easyIstrPath:easyIstrUserPath:PYTHONPATH
PY="/mnt/c/DEXCS/easyIstrPython/Python-3.12.9_withGiVtkSpGm/bin/python3.12.exe"
"$PY" 'C:\DEXCS\easyIstrPython\easyIstr\bin\unv2fistrEx.py' '..\unv\plate.unv' FistrModel
# → FistrModel.msh 生成（引数: <入力.unv> <出力prefix>）
```

## 4. モデル・単位系（重要）

- 形状: 100 × 20 × 5（長さ×幅×板厚）。メッシュ座標がこの値。
- **UNVの単位レコードは "SI: Meter" だが、100m板は非現実的。実際は 100mm 板と解釈**。
  （14-16kHzのスキャンや1次536Hzが100mm板と整合。100mなら1次≈0.5Hzで有り得ない）
- **単位系: mm-kg-s** を採用（座標mmのまま）。
  - ヤング率 E = 2.06e8（kg/(mm·s²)）、密度 ρ = 7.86e-6（kg/mm³）
  - 力 = mN、応力 = kPa、振動数 = Hz（時間が秒のため）
  - ※固有振動数は E/ρ で決まるので mm-tonne-s / m-kg-s でも同じHz。
- メッシュのグループ:
  - 要素: `plate`（TYPE=341 1次四面体, 5468要素, 1731節点）
  - 節点: `fix`（X=0面, 40節点, 完全固定）, `load`（X=100自由端, 36節点, 周期荷重）
  - 面: `press`, `otherS`（今回未使用）
  - モニタ節点 `node 2` = (100,20,5) 先端の角（load面上）
- 材料は `FistrModel.msh` に ITEM形式で埋め込み済み（!SECTION が MATERIAL=Steel を参照）。
  msh は CRLF改行なので編集時注意。

## 5. 固有値解析（001_eigen）— 完了

### 重要な注意点（ハマりどころ）
- **ソルバーは直接法 `!SOLVER,METHOD=DIRECT` を使う。**
  `METHOD=CG`（反復法）にすると固有値解析のシフト反転で収束せず、
  fistr1が数分間コアをフル稼働したまま出力ゼロでハングする（実際にハングした）。
- `!EIGEN` は「固有値数, 許容差, 最大反復数」。周波数応答で使うため **20モード** 取得。

### 実行
```bash
cd 001_eigen
~/local/frontistr/bin/fistr1
```

### 結果（固有振動数）
| モード | Hz | 種類 |
|---|---|---|
| 1 | 536 | Z(板厚)1次曲げ |
| 2 | 1640 | Y(幅)1次曲げ |
| 3 | 3303 | Z 2次曲げ |
| 4 | 4612 | ねじり |
| 5 | 8835 | Z 3次曲げ |
| … | … | mode8≈13999, mode9≈17055 |

### 梁理論との比較（ブログの主眼）
- オイラー・ベルヌーイ片持ち梁: fn = (βnL)²/(2π)·√(EI/(ρA L⁴)), βnL=1.875,4.694,7.855
- Z方向(板厚5mm)曲げ: 理論 414/2592/7258 Hz vs FEA 536/3303/8835 Hz（+22〜29%）
- Y方向(幅20mm)曲げ: 理論 1654 Hz vs FEA 1640 Hz（-0.8%, ほぼ一致）
- **考察**: 1次四面体は曲げ方向の要素数が少ないと剛性過大評価(ロッキング)。
  薄い板厚方向(要素2〜3個)は+30%高め、広い幅方向(要素十数個)は一致。
- ブログ: `001_eigen/docs/20260712_1_FrontISTR固有値解析_梁理論との比較.md/.html`（作成済み）

## 6. 周波数応答解析（002_freqResponse）— 完了

### 参照した公式チュートリアル
FrontISTR公式 `tutorial/17_freq_beam`（梁の周波数応答）が最も正確な書式リファレンス。
https://github.com/FrontISTR/FrontISTR/tree/master/tutorial/17_freq_beam

### 001_eigen の認識・参照方法

FrontISTRが `001_eigen` フォルダを自動認識しているわけではない。
`002_freqResponse` 側の入力ファイルに `../001_eigen/...` という相対パスを明示している。

- `002_freqResponse/FistrModel.cnt`
  - `!EIGENREAD` で `../001_eigen/0.log` を読む
  - 固有値・固有振動数の読み込み
- `002_freqResponse/hecmw_ctrl.dat`
  - `!MESH` で `../001_eigen/FistrModel.msh` を読む
  - `!RESULT,NAME=result-in,IO=IN` で `../001_eigen/FistrModel.res` を読む
  - 固有ベクトル（`FistrModel.res.0.1..20`）の読み込み

詳細は `docs/002_freqResponse_001_eigen_reference.md` に整理済み。

### .cnt の要点（FistrModel.cnt）
```
!SOLUTION,TYPE=DYNAMIC
!DYNAMIC
 11, 2                        # 2=周波数応答モード
 100, 1000, 90, 1000.0        # 開始Hz,終了Hz,step数,変位計算Hz ← スキャン範囲
 0.0, 6.6e-5                  # 開始/終了時間
 1, 1, 0.1, 0.0               # LOAD_CASE実部,虚部, Rm=0.1, Rk=0.0（減衰）
 10, 2, 2                     # sampling数, 出力指定(2=物理空間), nodeID=2
 1, 0, 0, 0, 0, 0             # モニタ内容: 変位のみ
!EIGENREAD
 ../001_eigen/0.log           # 固有値解析の結果(固有値)を読む
 1, 20                        # 読み込むモード範囲
!BOUNDARY
fix, 1, 3, 0.0
!FLOAD, LOAD CASE=1           # load面に周期荷重, Z方向(DOF3), 1.0
load, 3, 1.0
!SOLVER,METHOD=CG,PRECOND=1,...
```
- hecmw_ctrl.dat の `!RESULT,NAME=result-in,IO=IN → ../001_eigen/FistrModel.res` で
  固有ベクトルも読む。`!MESH → ../001_eigen/FistrModel.msh`。
- 2026-07-12時点で `!WRITE,RESULT` と `!WRITE,VISUAL` は削除済み。
  コンプライアンス曲線作成に不要な `FistrModel.res.*`、`FistrModel_dyna.res.*`、`*.pvtu`、`*.vtu` は出力しない。

### 「スキャン範囲」について（ユーザーが混乱した点）
- スキャン範囲 = 応答を計算する周波数の範囲（`!DYNAMIC`の2行目の開始Hz〜終了Hz）。
- **easyIstrマニュアルの設定画面(14000-16000)はデフォルト表示で、実際に使う値ではない。**
  マニュアルの実際の周波数応答は「1次固有振動数536Hzを見るため 100〜1000Hz, 90step(10Hz間隔)」。
- 最初14000-16000で計算してピークが出ず（536Hz共振が範囲外だった）、100-1000に修正して解決。

### 実行
```bash
cd 002_freqResponse
~/local/frontistr/bin/fistr1
```

### 結果
- モニタ節点(node2)の応答: **540Hz(サンプル点)に共振ピーク, 振幅 1.093e-2**。
  → easyIstrマニュアルの結果図（ピーク≈540Hz, ≈1.1e-2）とほぼ一致。
- 最小出力構成で再計算済み。002側には周波数応答の各ステップ `.res` と可視化用 `.pvtu/.vtu` は再生成されない。
- 周波数-応答データ: `0.log` から抽出 → `docs/compliance.csv`
- グラフ: `docs/img/compliance.png`（`graph.ipynb` で生成。フォント大・凡例/注記が重ならない配置）

### グラフ描画（graph.ipynb）
- `002_freqResponse/0.log` の `<Hz> [Hz] : <振幅>` 行を正規表現で抽出してmatplotlibで描画。
- ピーク(最大)を赤丸＋左側に矢印注記、凡例は右上。フォント14-16。

## 7. 残タスク（TODO）

- [ ] **周波数応答のブログ記事**（`002_freqResponse/docs/`）が未作成。
  固有値ブログ(`001_eigen/docs`)と同じテイスト（です・ます調、体言止め見出し、
  JINボックス `jin-gb-block/box-with-headline`、[mathjax]、冒頭に「こんにちは(@t_kun_kamakiri)」、
  環境メモ `FrontISTR 5.9 / WSL2環境に構築`）で `.md → .html` の順に作成する。
  内容案: 周波数応答とは / 固有値結果の引き継ぎ(!EIGENREAD, hecmw_ctrlのresult-in) /
  FLOAD設定 / スキャン範囲の考え方 / コンプライアンス波形(compliance.png) /
  公式チュートリアル17_freq_beamへのリンク。
- [ ] 固有値ブログに解析条件の図（メッシュ・モード形状のParaView画像）を入れるなら img/ に追加。

## 8. ブログ執筆ルール（このユーザーの好み。重要）

- **必ず .md を先に編集 → その後 .html に反映**（逆は不可）。
- 文体: フレンドリーな **です・ます調**。見出しは**体言止め**（疑問形・口語的な煽りは不可）。
  「ここで1つ疑問が湧きます」等の前振り・だらだら解説・「ちなみに」余談は削る。
- .html は WordPress ブロック形式。先頭に使い方コメントを入れない（貼付時に空段落になる）。
  数式は `\begin{align*}...\end{align*}`、インラインは `$...$`。
- 参考: `/mnt/d/work/002_CAE/frontistr/work/20260707_biMetal_heatFilm/docs` および
  `20260707_biMetal/docs` の完成記事、`20260707_biMetal/docs/template.html`。

## 9. よく使うコマンド早見

```bash
# 固有値解析
cd 001_eigen && ~/local/frontistr/bin/fistr1

# 周波数応答（001_eigenの結果を参照）
cd 002_freqResponse && ~/local/frontistr/bin/fistr1

# 0.log から周波数-応答を確認
grep '\[Hz\] :' 002_freqResponse/0.log
```
