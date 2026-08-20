# 011_Tji_DUMPW — FrontISTR内で感度行列WとVTKを出力する検証

DUMPWパッチ（`patch/frontistr_dumpw_tet.patch`）を当てた `fistr1` で、感度行列
$W = K^{-1}H$ の測定点差 $W_{\text{diff}}$ とそのVTKを、**FrontISTRだけで**出力する検証ケース。
手順の詳細は `docs/13_手順_FrontISTR内でW行列とVTKを出力.md` を参照。

## 入力ファイル

| ファイル | 役割 |
|---|---|
| `FistrModel.msh` | 570節点のQuad4_FEM_Tjiメッシュ（`009_Tji_H_direct` からコピー） |
| `FistrModel.cnt` | `!SOLVER,...,DUMPW=YES`（`DUMPEXIT` は付けない） |
| `hecmw_ctrl.dat` | 入出力設定 |
| `sensitivity_points.dat` | Point_A と Point_O のグローバル節点番号（`19 103`） |

## 実行

```bash
$HOME/src/FrontISTR-dumpw/build-dumpw/fistr1/fistr1 > run_dumpw.log 2>&1
```

## 出力（gitには含めない：再実行で作れる）

| ファイル | 内容 |
|---|---|
| `sensitivity_Wdiff.vtk` | 感度場ベクトル（ParaView用、フィールド名 `Sensitivity`） |
| `Wdiff_fistr.txt` | `global_node_id  wx wy wz` の表（数値比較用） |

## 検証結果

`009_Tji_H_direct/Wdiff_fistr_tji.npy`（Python版 `post/wdiff_adjoint.py` の結果）と比較して、
相対差 **2.4e-8**（倍精度の丸め誤差レベル）で一致。材料定数は両者そろえてある
（ヤング率 130000000.0、ポアソン比 0.27、線膨張係数 1.2e-5）。
