# 手順：Abaqus .inp → FrontISTR 変換と 全体剛性行列 K の出力

対象モデル：`sample/001_3DFEM/Quad4_structual/Inp_Data/Quad4_FEM_01.inp`
（C3D4＝線形四面体、425節点・1403要素、材料 FC300、Fixed/Force 節点セット）

3次元1次要素（四面体 341）で、FrontISTR と Python(自作FEM) の両方で K を出して比較するのが目的。

---

## 単位系（重要）

FrontISTRは単位系を明示せず、**入力値の整合性だけ**で決まる。このモデルは inp の値から
**mm-kg-s系**（整合単位系）と判断できる。

| 量 | 単位 | 値 → 物理的意味 |
|---|---|---|
| 長さ（座標） | mm | 0〜150 → 150mm長、30×30mm断面 |
| ヤング率 E / 応力 | kPa (=10³Pa) | `1.3e8` kPa = **130 GPa**（鋳鉄FC300）|
| 密度 | kg/mm³ | `7.4e-6` = 7400 kg/m³ |
| 熱膨張係数 | 1/K | `1.2e-5` |
| 力（CLOAD） | mN (=10⁻³N) | `-1000` = **−1 N** |
| 変位（結果） | mm | |
| 応力（結果） | kPa | |

換算の根拠：mm-kg-s系では `1 kg/(mm·s²) = 10³ Pa = 1 kPa`。
steelのplate（E=2.06e8→206GPa）と同じ規約。

**K比較には単位は無関係**：FrontISTRもPythonも同じ数値（E=1.3e8, 座標mm）を読むため、
K行列は同じ土俵で比較できる。単位系は「その数値が何GPaか」を解釈するときだけ効く。

---

## 全体の流れ

| Step | 内容 | 状態 |
|---|---|---|
| 1 | `.inp` を FrontISTR 形式（`.msh`/`.cnt`/`hecmw_ctrl.dat`）へ変換し、無改造fistr1で解けることを確認 | ✅ 完了 |
| 2 | FrontISTR ソースを改造し K を出力（環境変数ゲート）→ 再ビルド → K_fistr 取得 | 進行中 |
| 3 | Python(`Quad4_main.py`) で同じモデルの K を出力 | 未 |
| 4 | FrontISTR と Python の K を比較 | 未 |
| 5 | （後回し）温度荷重行列 H の出力 | 未 |

---

## Step 1：.inp → FrontISTR 変換（完了）

### 1-1. 変換スクリプト

`model/inp2fistr.py`（このモデル専用の最小コンバータ）。やっていること：

- `*NODE` → `!NODE`
- `*ELEMENT, TYPE=C3D4` → `!ELEMENT, TYPE=341, EGRP=body`
- `*NSET "Fixed..."` → `!NGROUP, NGRP=fix`
- `*NSET "Force..."` → `!NGROUP, NGRP=force`
- 材料を **HECMW形式で .msh に埋め込む**（`!MATERIAL, NAME=FC300, ITEM=2`：弾性＋密度）
- `!SECTION, TYPE=SOLID, EGRP=body, MATERIAL=FC300`

### 1-2. 実行コマンド

```bash
cd 20260810_KinvH/frontistr/model
python3 inp2fistr.py \
  ../sample/001_3DFEM/Quad4_structual/Inp_Data/Quad4_FEM_01.inp \
  001_K/FistrModel.msh
```

出力：`nodes=425, elems=1403, fix=25節点, force=節点2`。

### 1-3. 制御ファイル（`model/001_K/`）

- `FistrModel.cnt`：`!SOLUTION,TYPE=STATIC`、`!BOUNDARY fix,1,3,0.0`（完全固定）、
  `!CLOAD force,3,-1000.0`（検証用荷重）、`!SOLVER,METHOD=DIRECT`、`!MATERIAL FC300`。
- `hecmw_ctrl.dat`：`!MESH FistrModel.msh` / `!CONTROL FistrModel.cnt` / `!RESULT ... IO=OUT`。

### 1-4. 実行（無改造fistr1で妥当性確認）

```bash
cd 001_K
~/local/frontistr/bin/fistr1
```

結果：`### Relative residual = 1.97E-13`、`FrontISTR Completed !!`、`FistrModel.res.0.*` 出力。
→ 変換モデルは正しく、K も内部で正しく組めていると判断できる。

### ハマりどころ（メモ）

- **EGRP/NGRP に `ALL` は使えない**（予約語 `HECMW-IO-E0003`）。→ `body` などにする。
- **`SECTION: MATERIAL not found`**（`E1025`）：材料は `.cnt` だけでなく
  **`.msh` に HECMW形式で埋め込む**必要がある（`!MATERIAL, NAME=..., ITEM=2` ＋ `!ITEM=...`）。

---

## Step 2：FrontISTR で K を出力（次の作業）

方針：通常実行を壊さないよう、**環境変数 `FSTR_EXPORT_KH=1` でゲート**した
K出力（MatrixMarket 形式）をソースに追加し、`build-codex` で再ビルドする。

- K は `hecMAT`（BSRブロック格納）から (n_dof × n_dof) の MatrixMarket へ展開。
- 出力点は「AddBC の前（生の全体剛性行列）」を基本とする（自作FEMの `make_K` と対応させるため）。
- 併せて「内部節点番号 → inp節点ID」の対応表も出力（比較時の並べ替え用）。

（詳細と実装は `06_DESIGN.md` / `07_WORK_LOG.md` を参照）

---

## Step 3以降

- Python：`Quad4_main.py` の `inpfileName` を `Quad4_FEM_01.inp` に変更して K を組み立て、保存。
- 比較：節点順・自由度順をそろえて `‖K_fistr − K_python‖` を評価。
- 温度荷重 H：K 比較の後に着手（Python版Hはユーザーが別途提示予定）。
