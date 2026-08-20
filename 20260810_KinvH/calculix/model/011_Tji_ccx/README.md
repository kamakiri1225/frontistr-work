# 011_Tji_ccx — CalculiX で K・H・W・VTK を出す検証ケース（C3D4）

改造版 CalculiX（`patch/ccx_2.21_dumpkh.patch`）で、FrontISTR と同じ Quad4_FEM_Tji（570 節点、
一次四面体 C3D4）の `K`・`H`・`W`・VTK を出す。手順の詳細は
`calculix/docs/01_手順_CalculiXでK_H_W_vtk出力.md`。

## 入力ファイル

| ファイル | 役割 |
|---|---|
| `Quad4_FEM_Tji.inp` | 元メッシュ＋材料（Abaqus/CalculiX 形式、C3D4） |
| `mesh.inp` | 上から `*PLASTIC` を除いた線形弾性版 |
| `ccx_tji.inp` | 解析デック（include ＋ 境界・温度・ステップ）。Point_A=19, Point_O=103, 固定=NFIX |

## 実行

```bash
# K・H・W・VTK を1回で（すべて CalculiX 内部で計算）
export OMP_NUM_THREADS=4
CCX_DUMPKH=1 $HOME/src/calculix_build/CalculiX/ccx_2.21/src/ccx_2.21 ccx_tji
```

- 測定点は `sensitivity_points.dat`（`19 103`）で指定。無いとエラーで停止する。
- （参考）`python3 ../../post/ccx_wdiff.py --workdir . --inp Quad4_FEM_Tji.inp` でも
  K・H から W・VTK を作れる（内部計算と一致。通常は不要）。

## 出力（gitには含めない：再実行で作れる）

| ファイル | 内容 |
|---|---|
| `K.mtx` | 剛性 K（active DOF, MatrixMarket 対称）neq=1647 |
| `H.mtx` | 温度荷重 H（active DOF 行 × 節点列） |
| `nactdof.txt` | (節点, 方向)→方程式番号（0以下=固定） |
| `Wdiff_ccx.txt` | 感度 Wdiff（`node wx wy wz`） |
| `sensitivity_Wdiff_ccx.vtk` | Wdiff の VTK（ParaView） |

## 結果

FrontISTR DUMPW（`../../../model/011_Tji_DUMPW/Wdiff_fistr.txt`）と相関 0.9995・相対差約 3% で一致。
