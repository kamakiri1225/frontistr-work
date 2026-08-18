# 008_Tji_compare

## 目的

`sample/002_thermalSensitive/Inp_Data/ThermoSenseAnalyzer_00.py`（Quad4という名前だが
実体はC3D4四面体一次要素の自作Python FEM）が計算するK・H・Wと、FrontISTRが同じモデルで
計算するK・H・Wを、**同一メッシュ・同一材料定数**で数値比較するための作業フォルダである。

`ThermoSenseAnalyzer_00.py`自体は`setting/settings.yml`が本リポジトリに無く単体では動かせない
（CLI引数・マルチプロセスなど比較に不要な処理も多い）ため、実行はせず、
`post/python_H_tji.py`に同じ数式（`make_D`/`make_CTE`/`make_B`/`make_He`/`make_Ke`）だけを
移植して使っている。移植時に、`ThermoSenseAnalyzer_00.py`がハードコードしている
E=130000.0, CTE=1e-5ではなく、`Quad4_FEM_Tji.inp`に実際に書かれている値
（E=130000000, ν=0.27, density=7.4e-06, CTE=1.2e-05）を使った
（ハードコード値は今回のinpの実際の材料定数と一致していない）。

## モデル

`Quad4_FEM_Tji.inp`（*ELEMENT, TYPE=C3D4）を`post/inp_to_fistr_msh.py`でFrontISTR形式
（`FistrModel.msh`, `!ELEMENT TYPE=341`）に変換した。570節点、1699要素。

- 固定節点（`Fixed`のNSET）: 21節点、全自由度固定
- Point_A（節点19）= 測定ツール点、Point_O（節点103）= 基準点
  （`ThermoSenseAnalyzer_00.py`の`tool`/`origin`に相当）

## 作った・使ったスクリプト

| スクリプト | 内容 |
|---|---|
| `post/inp_to_fistr_msh.py` | `Quad4_FEM_Tji.inp` → `FistrModel.msh`/`hecmw_ctrl.dat` 変換 |
| `post/python_H_tji.py` | Python側でK・H・Wを直接計算（`ThermoSenseAnalyzer_00.py`と同じ数式、フェーズ別に時間計測） |
| `post/build_H_tji.py` | FrontISTR標準機能のみで、570節点に単位温度を1つずつ与えて570回実行しHを組み立てる（`model/004_H/build_H.py`のTji版） |
| `post/compute_kinvH_tji.py` | FrontISTR側のK・HからW=K⁻¹Hを計算（`model/004_H`用`compute_kinvH.py`のTji版、時間計測付き） |
| `post/write_sensitivity_vtk.py` | WdiffをParaViewで見えるVTK(legacy ASCII)として書き出す汎用スクリプト |

## H・K・Wの比較結果

| 項目 | 比較対象 | 最大絶対差 | 相対差(Frobenius) |
|---|---|---|---|
| H（生、境界条件なし） | `H_python_tji.npz` vs `H_fistr_tji.npz` | 5.0e-07 | 1.5e-12 |
| K（境界条件適用後） | `K_python_tji_bc.mtx` vs `K_fistr_tji.mm` | 4.9e-02 | 1.3e-12 |
| Wdiff（節点19-103, K⁻¹Hから抽出） | `Wdiff_python_tji.npy` vs `Wdiff_fistr_tji.npy` | 1.2e-11 | 2.4e-08 |

いずれも数値誤差レベルで一致。独立に実装したPython版の数式とFrontISTRが、
同一モデルに対して同じK・H・Wを計算できていることを確認した。

## 計算時間の比較

| 出力 | Python (`python_H_tji.py`) | FrontISTR |
|---|---|---|
| K（境界条件適用後） | 組み立て 0.45 s（H と同じループ内） | 0.79 s（`!BOUNDARY`+`DUMPTYPE=MM`、1回実行） |
| H（生） | 組み立て 0.45 s + 保存 0.07 s | 標準機能570回実行: **484 s** / DUMPHパッチ1回実行: **1.81 s**（[`../009_Tji_H_direct`](../009_Tji_H_direct/README.md)、約270倍高速） |
| W = K⁻¹H | BC処理 0.17 s + 求解 0.26 s | 読込 0.34 s + 求解 0.28 s |
| 合計 | 約2.0 s | 約485 s（Hの節点を1つずつ計算する処理が支配的） |

上記の「標準機能570回実行」が極端に遅いのは、**改造していない標準機能だけで570回fistr1を
再実行**してRHSを1列ずつ集めているため（`model/004_H/build_H.py`と同じ方式）。
`model/005_H_direct`で使った`DUMPH=YES`パッチ（`patch/frontistr_dumph_341.patch`）を
このモデル用にビルドし直し、1回実行で検証した結果は[`../009_Tji_H_direct`](../009_Tji_H_direct/README.md)
を参照。1.81 sまで短縮され、570回版・Python版のいずれとも数値一致した。

## ParaViewで見えるようにしたもの

`Wdiff`（節点19-103間の相対変位が、各節点の単位温度に対してどれだけ変化するかを表す
(3, 570)の行列）を、`post/write_sensitivity_vtk.py`で節点ベクトル場としてVTKに書き出した。

- `Wdiff_python_tji.vtk`（フィールド名 `Sensitivity_Python`）
- `Wdiff_fistr_tji.vtk`（フィールド名 `Sensitivity_FrontISTR`）

どちらもlegacy VTK ASCII形式（`DATASET UNSTRUCTURED_GRID`, `VECTORS ... double`）で、
ParaViewで直接開ける。`python-vtk`（`vtkUnstructuredGridReader`）でパース可能なことを確認済み。
値は変位そのものではなく感度（temperature-to-displacement sensitivity）なので、
フィールド名は`Displacement`ではなく`Sensitivity`にしている
（元の`ThermoSenseAnalyzer_00.py`の`outputvtk()`は`Displacement`という名前で
同じ中身を出力しており、紛らわしい点に注意）。

## 再現手順

```bash
cd 20260810_KinvH
python3 post/inp_to_fistr_msh.py
python3 post/python_H_tji.py
# 以下はFrontISTR実行が必要（標準fistr1、~/local/frontistr/bin/fistr1）
#  - K: model/008_Tji_compare/FistrModel.cnt に !BOUNDARY, !CLOAD, DUMPTYPE=MM, DUMPEXIT=YES を書いて1回実行 → K_fistr_tji.mm にリネーム
#  - H: python3 post/build_H_tji.py   （570回実行、約8分）
python3 post/compute_kinvH_tji.py
python3 post/write_sensitivity_vtk.py --wdiff model/008_Tji_compare/Wdiff_python_tji.npy --out model/008_Tji_compare/Wdiff_python_tji.vtk --field-name Sensitivity_Python
python3 post/write_sensitivity_vtk.py --wdiff model/008_Tji_compare/Wdiff_fistr_tji.npy --out model/008_Tji_compare/Wdiff_fistr_tji.vtk --field-name Sensitivity_FrontISTR
```

## 注意（.gitignore）

`*.mtx` `*.mm` `*.npy` `*.npz` `0.log` `FSTR.*` `dump_matrix_*` はすべて`.gitignore`で
除外されるため、このフォルダの計算結果はローカルのみに存在しGitHubにはpushされない。
`*.vtk`は`.gitignore`の対象外なので、そのままpushするとやや重い（約95KB×2）。
