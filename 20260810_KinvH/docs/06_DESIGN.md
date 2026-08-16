# FrontISTR カスタマイズ：全体剛性行列 K・温度荷重変換行列 H の出力と K⁻¹H の計算

> **2026-08-11 更新:** この文書のソース改造案は初期設計。
> 現在は `!SOLVER,DUMPH=YES` を追加し、既存の `TLOAD_C3` から要素タイプ341のHを出力する
> 検証済みパッチがある。現在の実装とビルド方法は
> `docs/05_手順_FrontISTR_DUMPH追加とビルド.md`、経緯は `docs/07_WORK_LOG.md` を参照。

## 目的

FrontISTR（静的熱応力解析）をカスタマイズし、次を得る。

1. **全体剛性行列 K**（n_dof × n_dof、疎行列）
2. **温度荷重変換行列 H**（n_dof × n_node）— 節点温度ベクトル T を節点等価熱荷重ベクトル f に変換する行列
3. **K⁻¹H**（n_dof × n_node）— 節点温度 → 節点変位 の変換行列（後処理プログラムで計算）

関係式：

```
f_thermal = H · T           （節点温度 → 節点熱荷重）
K · u      = f_thermal        （平衡方程式）
=> u = K⁻¹ · f_thermal = (K⁻¹H) · T   （節点温度 → 節点変位）
```

## 環境

- ソース: `/home/kamakiri/src/FrontISTR`（git `7f48eae0`）
- ビルド: CMake、ビルドディレクトリ `build-codex`
  - コンパイラ `/usr/bin/f95`(gfortran)、`CMAKE_BUILD_TYPE=RELEASE`
  - `WITH_MPI=OFF`, `WITH_MKL=OFF`, `WITH_MUMPS=OFF`, `WITH_LAPACK=ON`
  - install prefix: `/home/kamakiri/local/frontistr`
- 単一ドメイン（MPI無効）なので、全体行列がそのままローカル行列＝グローバル行列。並列組み立ての考慮不要。
- 再ビルド: `cd build-codex && make -j` （動作確認済み）

## H の定義と導出（線形・等方の仮定）

要素温度荷重は `fistr1/src/lib/static_LIB_3d.f90` の `TLOAD_C3` で計算される。積分点ごとに：

```
TEMPC = Σ_j N_j T_j            （N = 形状関数, TT = 節点温度）
EPSTH(1:3) = α (TEMPC - Tref)   （等方、温度依存 α は近似的に一定とみなす）
SGM   = D · EPSTH
VECT += Bᵀ · SGM · wg           （要素熱荷重ベクトル）
```

節点温度 T_j に関して線形化すると、`∂TEMPC/∂T_j = N_j` なので要素 H：

```
H_e[:, j] = Σ_gauss ( Bᵀ · D · a ) · N_j · wg,   a = α[1,1,1,0,0,0]ᵀ
```

- サイズ：`(nn·3) × nn`（nn=要素節点数）
- `Bᵀ·D·a` は「単位温度あたりの節点熱応力→節点力」ベクトル
- **線形性の前提**：α温度非依存（`!EXPANSION_COEFF` の定数値）、等方、初期温度 T0 = Tref。
  これらが成り立つとき H は温度に依存しない定数行列になる。

グローバル H は要素 H_e を「行=節点自由度、列=節点番号」で散らして組み立てる。

## 実装方針（ソース改造）

通常実行を壊さないため、**環境変数 `FSTR_EXPORT_KH=1` でゲート**した opt-in 出力にする。

### (A) K の出力

既存の行列ダンプ機構 `hecmw_mat_dump`（`hecmw1/src/solver/matrix/hecmw_matrix_dump.f90`）を利用。
本バージョンは制御カードからの有効化パスが無いため、以下いずれか：

- 案1: ソルバー呼び出し直前に `hecmw_mat_set_dump(hecMAT, HECMW_MAT_DUMP_TYPE_MM)` を
  env ゲートで呼ぶ（MatrixMarket 出力 `*.mm`）。
- 案2: 独自に COO(MatrixMarket) 形式で K を書き出すルーチンを追加（H と同じ書式に揃う）。

→ **案2 を採用**：K も H も同じ MatrixMarket coordinate 形式で出し、後処理を単純化。
   K は `hecMAT`（BSR 3×3 ブロック：D(対角ブロック), AU/AL(上/下三角), index/item）から
   グローバル (n_dof × n_dof) の COO へ展開して出力。

### (B) H の出力

新規ファイル `fistr1/src/analysis/static/fstr_export_KH.f90`（モジュール）を追加し：

1. `TLOAD_MAT_C3`（`TLOAD_C3` の派生）：要素 H_e を返す。
2. `assemble_export_H`：全要素ループ → H_e を COO に散らす（対象要素タイプ=3D solid をまず実装。341/342/361 等）。
3. `export_matrix_market`：K・H を MatrixMarket 形式で書く共通ルーチン。

呼び出し位置：静的解析で K 組み立て済み・温度荷重計算の直後、ソルブ前
（`fstr_solve_lineq` 呼び出し直前、`fstr_ass_load` の後）。`fstr_static_ass` 系または
`fstr_solve_NLGEOM`/`fstr_linear_static` の該当箇所に env ゲートで挿入。

### (C) 出力ファイル

作業ディレクトリに：

- `K.mtx`  … MatrixMarket coordinate, n_dof × n_dof
- `H.mtx`  … MatrixMarket coordinate, n_dof × n_node
- `dof_map.txt` … 行=グローバル自由度 → (節点番号, 方向) の対応（検証用）

## K⁻¹H の計算（後処理、`post/kinvh.py`）

FrontISTR とは独立。scipy で：

```
K = mmread('K.mtx').tocsc()
H = mmread('H.mtx').toarray()      # n_dof × n_node
X = spsolve(K, H)                  # 列ごとに K X = H を解く → X = K⁻¹H
```

境界条件（固定自由度）の扱いに注意：

- FrontISTR がダンプする K は境界条件処理後（固定自由度に1を立てるペナルティ/消去後）の可能性がある。
  ダンプの取得点によって、拘束の入り方が変わるため、**ダンプ位置＝ソルブ直前**にして
  「実際に解いている K」を出す。これにより K⁻¹H が FrontISTR の変位解と整合する。

## 検証（`model/`）

小さな熱膨張モデル（数十節点の片持ち・拘束あり）で：

1. 一様温度上昇 ΔT を全節点に与えて FrontISTR で解き、変位 u_fistr を得る。
2. 同じモデルで K, H を出力。
3. `post/kinvh.py` で u_pred = (K⁻¹H)·T を計算。
4. `u_pred ≈ u_fistr` を確認（相対誤差 < 1e-8 程度）。

## TODO / ステータス

- [x] ソース構造・TLOAD_C3・行列ダンプ機構の調査
- [x] ビルド確認（build-codex で再ビルド可能）
- [x] K⁻¹H 後処理プログラム（synthetic self-test 付き）
- [x] 検証モデル作成（`model/003_Htest`）
- [x] Fortran改造の試作（`DUMPH=YES`、要素タイプ341）
- [x] 検証用コピーで再ビルドし、`H_matrix.mtx` を出力
- [x] `H[:,2]` と標準FrontISTRの温度荷重RHSが完全一致
- [ ] `/home/kamakiri/src/FrontISTR` 本体へ検証済みパッチを適用・インストール
- [ ] K⁻¹HとFrontISTR変位の比較（Python後処理を行う段階で実施）

## 未確定事項（要ユーザー確認）

- H の定義：現状「節点温度→節点変位」（H=∫BᵀDαN dV）で進行中。
  「要素温度→節点荷重」など別定義が必要なら列の意味が変わる。
- 対象要素タイプ：まず 3D solid（341/342 等）。シェル/ビーム/2D は必要に応じ追加。
