# calculix/ — CalculiX 版の K・H・W・VTK 出力（熱感度）

このフォルダは、FrontISTR で作った熱感度解析（`K`・`H`・`W = K^-1 H`・VTK）を
**CalculiX (ccx) でも同じようにできるか確認**した作業一式。**FrontISTR 側とは分離**してある
（親フォルダ `20260810_KinvH` は基本 FrontISTR 用）。対象は**一次四面体 C3D4 のみ**。

## 中身

| フォルダ/ファイル | 内容 |
|---|---|
| `docs/01_手順_CalculiXでK_H_W_vtk出力.md` | 導入（ソースビルド）・改造（どのファイルを変えたか＋数式とプログラム）・実行・結果 |
| `patch/ccx_2.21_dumpkh.patch` | CalculiX 改造パッチ（`linstatic.c`。`CCX_DUMPKH=1` で **K・H・W・VTK** を出力） |
| `model/011_Tji_ccx/` | 入力デック（`ccx_tji.inp` / `mesh.inp` / `Quad4_FEM_Tji.inp` / `sensitivity_points.dat`）と出力 |
| `post/ccx_wdiff.py` | （参考）K・H から W・VTK を作る Python 後処理。**W は今は CalculiX 内部で出るので通常は不要** |

## ざっくり手順

```bash
# 1) CalculiX をソースからビルド（詳細は docs/01）
#    SPOOLES を build → linstatic.c にパッチ → make → ccx_2.21

# 2) K・H・W・VTK を出す（改造版 ccx を CCX_DUMPKH=1 で。W も VTK も CalculiX 内部で計算）
cd model/011_Tji_ccx
export OMP_NUM_THREADS=4
CCX_DUMPKH=1 $HOME/src/calculix_build/CalculiX/ccx_2.21/src/ccx_2.21 ccx_tji
#   -> K.mtx, H.mtx, nactdof.txt, Wdiff_ccx.txt, sensitivity_Wdiff_ccx.vtk
```

- 測定点 Point_A / Point_O は `model/011_Tji_ccx/sensitivity_points.dat`（`19 103`）で指定。
  このファイルが無いとエラーで停止する（FrontISTR DUMPW と同じ）。

## 結果

FrontISTR DUMPW（`../model/011_Tji_DUMPW`）と比較して、感度 `Wdiff` は**相関 0.9995・
相対差 約 3%**で一致（支配成分は完全一致）。**CalculiX でも同じ K・H・W・VTK 出力が
（ソルバ内部で）できる**ことを確認した。残る数 % は独立した 2 つの FEM コードの一次四面体の
実装差。4 並列（OMP=4）の実測は FrontISTR 約 0.16–0.19 s / CalculiX 約 0.13–0.15 s（同規模）。
