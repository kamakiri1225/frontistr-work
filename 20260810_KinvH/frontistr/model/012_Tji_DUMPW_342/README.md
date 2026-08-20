# 012_Tji_DUMPW_342 — 二次四面体（342, C3D10）でのK/H/W/VTK出力検証

DUMPWパッチ（`patch/frontistr_dumpw_tet.patch`）を当てた `fistr1` で、**二次要素メッシュ**の
`K`・`H`・`W`・`VTK` を**1回の実行**で出力する検証ケース。手順・理論・速度比較は
`docs/14_手順_1次2次要素のW出力とvtk比較.md` を参照。

## メッシュ

一次版 `011_Tji_DUMPW/FistrModel.msh`（341, 570節点）を
`post/convert_341_to_342.py` で二次化したもの。

- 角節点570 + 中間節点2744 = **3314節点**、要素1699（各四面体が4→10節点）
- 固定節点群 `fix`：角21 + 両端固定辺の中点44 = 65節点

```bash
python3 ../../post/convert_341_to_342.py \
    ../011_Tji_DUMPW/FistrModel.msh FistrModel.msh
```

## 入力ファイル

| ファイル | 役割 |
|---|---|
| `FistrModel.msh` | 二次四面体メッシュ（342） |
| `FistrModel.cnt` | `!SOLVER,...,DUMPTYPE=MM,DUMPW=YES`（`DUMPEXIT` は付けない） |
| `hecmw_ctrl.dat` | 入出力設定 |
| `sensitivity_points.dat` | Point_A / Point_O のグローバル節点番号（先頭に `#Point_A, Point_O` のコメント可） |

## 実行

```bash
export OMP_NUM_THREADS=4
$HOME/src/FrontISTR-dumpw/build-dumpw/fistr1/fistr1 > run_dumpw.log 2>&1
```

## 出力（gitには含めない：再実行で作れる）

| ファイル | 内容 |
|---|---|
| `dump_matrix_1_0.mm` | K（境界条件適用後、MatrixMarket） |
| `H_matrix.mtx` | H（温度荷重行列。(行,列)で整列・重複合算済み、22.9万エントリ） |
| `sensitivity_Wdiff.vtk` | W（ParaView用、VTK_QUADRATIC_TETRA / セル型24） |
| `Wdiff_fistr.txt` | W（`global_node_id wx wy wz`） |

## 検証結果

同じ実行で出した `K`・`H` を読み込んでPython（`scipy`）でアジョイント法をやり直した結果と比較して、
相対差 **1.1e-7**（倍精度の丸め誤差レベル）で一致。角節点・固定節点・中間節点のいずれの列も一致。
二次要素でもDUMPWのWは正しい。
