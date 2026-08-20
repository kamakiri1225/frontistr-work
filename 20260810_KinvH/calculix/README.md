# calculix/ — CalculiX 版の K・H・W・VTK 出力（熱感度）

このフォルダは、FrontISTR で作った熱感度解析（`K`・`H`・`W = K^-1 H`・VTK）を
**CalculiX (ccx) でも同じようにできるか確認**した作業一式。**FrontISTR 側とは分離**してある
（親フォルダ `20260810_KinvH` は基本 FrontISTR 用）。対象は**一次四面体 C3D4 のみ**。

## 中身

| フォルダ/ファイル | 内容 |
|---|---|
| `docs/01_手順_CalculiXでK_H_W_vtk出力.md` | 導入（ソースビルド）・改造（どのファイルを変えたか）・実行・結果の手順書 |
| `patch/ccx_2.21_dumpkh.patch` | CalculiX 改造パッチ（`linstatic.c`。`CCX_DUMPKH=1` で K・H・nactdof を出力） |
| `model/011_Tji_ccx/` | 入力デック（`ccx_tji.inp` / `mesh.inp` / `Quad4_FEM_Tji.inp`）と出力 |
| `post/ccx_wdiff.py` | K・H から W（アジョイント）と VTK を作る後処理 |

## ざっくり手順

```bash
# 1) CalculiX をソースからビルド（詳細は docs/01）
#    SPOOLES を build → linstatic.c にパッチ → make → ccx_2.21

# 2) K・H・nactdof を出す（改造版 ccx、環境変数で有効化）
cd model/011_Tji_ccx
CCX_DUMPKH=1 $HOME/src/calculix_build/CalculiX/ccx_2.21/src/ccx_2.21 ccx_tji

# 3) W・VTK を出す
python3 ../../post/ccx_wdiff.py --workdir . --inp Quad4_FEM_Tji.inp
```

## 結果

FrontISTR DUMPW（`../model/011_Tji_DUMPW`）と比較して、感度 `Wdiff` は**相関 0.9995・
相対差 約 3%**で一致（支配成分は完全一致）。**CalculiX でも同じ K・H・W・VTK 出力ができる**
ことを確認した。残る数 % は独立した 2 つの FEM コードの一次四面体の実装差。
