# post/ スクリプト一覧と使い方

このフォルダのスクリプトは大きく4グループに分かれる。

1. **ユーティリティ**（FrontISTRの行列ダンプを読み書きする共通部品）
2. **425節点モデル用**（`model/001_K`〜`006_KinvH_test`、FrontISTRから取り出したK・Hと
   自作Python FEM（`sample/001_3DFEM`）を比較する一連の検証）
3. **Tji（570節点）モデル用**（`model/008_Tji_compare`, `009_Tji_H_direct`、
   `sample/002_thermalSensitive/Inp_Data/ThermoSenseAnalyzer_00.py`と同じ数式で
   FrontISTRの結果と数値比較する一連の検証）
4. **Tjiリファインメッシュ（3314節点）用**（`model/010_Tji_fine_H_direct`、
   3のメッシュを8分割リファインしたより大きい問題サイズでの同じ検証）

## 1. ユーティリティ

| スクリプト | 用途 |
|---|---|
| `read_fistr_matrix.py` | FrontISTRの行列ダンプ（`.csr`, `.mm`）を`scipy.sparse`に読み込むモジュール。`read_csr` / `read_mm` / `read_rhs`を提供。単独実行すると対称性チェックと対角の様子を表示する。 |
| `csr_to_mtx_csv.py` | `.csr` / `.mm` / `.npz`を MatrixMarket(`.mtx`)とCOO形式CSV(`row,col,value`)に変換する。`--dense`で密行列CSVも作れる（大きい）。 |

## 2. 425節点モデル用（K・H・K⁻¹Hの検証）

対象モデル: `model/001_K`（K）→`004_H`（Hを節点1つずつ計算して構築）→
`005_H_direct`（DUMPHで1回出力）→`006_KinvH_test`（K⁻¹Hの変位を検証）。
比較相手は`sample/001_3DFEM/Quad4_structual`の自作Python FEM。

| スクリプト | 用途 | 主な入出力 |
|---|---|---|
| `K_dense_compare.py` | FrontISTRのK(`model/001_K/K_bc.csr`)とPythonのK(`sample/001_3DFEM/Quad4_structual/K_python_bc.npz`)を、節点番号+成分でラベル付けした密行列CSVにして比較する。Python側は節点内x,y入替の並び替えが必要。 | 出力: `model/001_K/K_fistr_table.csv` / `K_python_table.csv` / `K_diff_table.csv` |
| `compare_K.py` | 上と同じ比較をCSV出力なしで、相対差・最大絶対差だけ表示する簡易版。 | 引数: `<K_fistr> <K_python>`（省略時は001_Kのデフォルトパス） |
| `kinvh.py` | 任意の`.mtx`のKとHから`X=K⁻¹H`を計算する汎用CLI。`--selftest`で合成行列による自己テストも可能。 | `python3 kinvh.py --K K.mtx --H H.mtx --out KinvH` |
| `compute_kinvH.py` | `model/001_K/K_bc.csr`と`model/004_H/H_fistr.npz`から`W=K⁻¹H`を計算し、境界条件（固定節点の行を0処理）まで込みで扱う425節点モデル専用版。`--diff N1 N2`で2点間の相対変位専用行列`Wdiff`も作れる。 | 出力: `model/004_H/KinvH.npy`, `Wdiff_{N1}_{N2}.npy` |
| `validate_kinvH.py` | `compute_kinvH.py`が作った`KinvH.npy`を使い、全節点T=100℃を与えた予測変位と、FrontISTRが実際に解いた変位(`model/006_KinvH_test/FistrModel.res.0.1`)を比較する。 | 結果: `model/006_KinvH_test/validate_report.txt` |
| `compare_H.py` | DUMPHが1回で直接出力したH(`model/005_H_direct/H_matrix.mtx`)と、節点を1つずつ計算して組み立てたH(`model/004_H/H_fistr.mtx`)を比較する。 | 結果: `model/005_H_direct/H_compare_report.txt` |

### 425節点モデルの実行手順

```bash
cd 20260810_KinvH
python3 post/compute_kinvH.py --diff 283 100   # K^-1H = W を再計算（KinvH.npy, Wdiff_283_100.npy）
python3 post/validate_kinvH.py                 # Wによる予測変位とFrontISTR解を比較
python3 post/compare_H.py                      # DUMPH直接出力 vs 節点を1つずつ計算して求めたHを比較
python3 post/compare_K.py                      # FrontISTR K vs Python K
```

## 3. Tji（570節点）モデル用（ThermoSenseAnalyzer_00.pyとの比較）

対象モデル: `sample/002_thermalSensitive/Inp_Data/Quad4_FEM_Tji.inp`
（570節点・1699要素・C3D4、Point_A=節点19・Point_O=節点103）。
`ThermoSenseAnalyzer_00.py`自体は`setting/settings.yml`が無く単体実行できないため、
同じ数式を移植したPython実装と、FrontISTR（標準機能／DUMPH改造版の両方）の
3通りでH・K・Wを計算し、突き合わせている。

| スクリプト | 用途 | 主な入出力 |
|---|---|---|
| `inp_to_fistr_msh.py` | `Quad4_FEM_Tji.inp`（Abaqus形式）をFrontISTR形式（`!ELEMENT TYPE=341`など）に変換する。`parse_inp()`は他のTji系スクリプトからも再利用している。 | 出力: `model/008_Tji_compare/FistrModel.msh`, `hecmw_ctrl.dat` |
| `python_H_tji.py` | `ThermoSenseAnalyzer_00.py`と同じ数式（`make_D`/`make_CTE`/`make_B`/`make_He`/`make_Ke`）で、H・K（境界条件適用後）・W=K⁻¹Hを直接計算する。フェーズ別（組み立て/保存/境界条件/求解）に時間計測する。 | 出力: `model/008_Tji_compare/H_python_tji.npz`, `K_python_tji_bc.mtx`, `Wdiff_python_tji.npy` |
| `build_H_tji.py` | FrontISTR**標準機能のみ**で、570節点に単位温度を1つずつ与えて570回`fistr1`を実行し、出てきたRHSを列として集めてHを組み立てる（節点を1つずつ計算する方法、`model/004_H/build_H.py`のTji版）。約8分かかる。 | 出力: `model/008_Tji_compare/H_fistr_tji.npz`, `.mtx` |
| `compute_kinvH_tji.py` | FrontISTR側のK・Hから`W=K⁻¹H`を計算し、Point_A(19)-Point_O(103)の相対変位用`Wdiff`を抜き出す。時間計測付き。`--workdir`/`--k`/`--h`/`--out`でフォルダとファイル名を指定でき、`--mesh-npz`でリファインメッシュ（4節）にも対応する。既定値は`model/008_Tji_compare`向け。 | 例: `--workdir model/009_Tji_H_direct --k K_fistr_tji.mm --h H_matrix.mtx --out Wdiff_fistr_tji.npy` |
| `write_sensitivity_vtk.py` | `Wdiff`（3×節点数の感度行列）をParaViewで開けるVTK(legacy ASCII)に書き出す汎用スクリプト。Python側・FrontISTR側どちらの`Wdiff`にも使える。`--mesh-npz`でリファインメッシュにも対応。 | `--wdiff <.npy> --out <.vtk> --field-name <名前> [--mesh-npz <mesh_fine.npz>]` |

このほか、`sample/002_thermalSensitive/Inp_Data/ThermoSenseAnalyzer_standalone.py`は
`python_H_tji.py`と同じ内容を、`ThermoSenseAnalyzer_00.py`と同じフォルダに置いて
そこで完結させたもの（`parse_inp`も内蔵、`post/`への依存なし）。出力先は
`sample/002_thermalSensitive/Inp_Data/Results/`。どちらを使っても同じ結果になる
（H行列が完全一致することを確認済み）。

**K・Hを1回の実行で同時に取得するコツ**: `!BOUNDARY`（RHSを非ゼロにする）＋
`!TEMPERATURE`＋`DUMPH=YES`＋`DUMPTYPE=MM`＋`DUMPEXIT=YES`を同時に指定すると、
改造版fistr1の1回の実行で境界条件適用後のK(`dump_matrix_1_0.mm`)とHの生値
(`H_matrix.mtx`)が両方出力される（`docs/11_...md`のセクション1で検証）。
`009_Tji_H_direct`・`010_Tji_fine_H_direct`はこの方式でK・Hを1回の実行にまとめている。

### Tjiモデルの実行手順（計算実行 → FrontISTRとPythonの比較）

```bash
cd 20260810_KinvH

# 1. メッシュ変換（Quad4_FEM_Tji.inp -> FrontISTR形式）
python3 post/inp_to_fistr_msh.py

# 2. Python側でH・K・Wを直接計算（数秒）
python3 post/python_H_tji.py
#   同じ内容を ThermoSenseAnalyzer_00.py のフォルダで実行したい場合:
#   cd sample/002_thermalSensitive/Inp_Data && python3 ThermoSenseAnalyzer_standalone.py

# 3a. FrontISTR側のH: 標準機能だけで570回実行（節点を1つずつ計算、約8分）
python3 post/build_H_tji.py

# 3b. FrontISTR側のK・H: DUMPHパッチ版で1回実行（約2秒、要ビルド）
#     !BOUNDARY + !TEMPERATURE + DUMPH=YES + DUMPTYPE=MM + DUMPEXIT=YES を指定すれば
#     K・Hが同時に出る。ビルド手順は docs/05_手順_FrontISTR_DUMPH追加とビルド.md 、
#     結果は model/009_Tji_H_direct/README.md を参照
cd model/009_Tji_H_direct && $HOME/local/frontistr-dumph/bin/fistr1 && \
  mv dump_matrix_1_0.mm K_fistr_tji.mm && cd -

# 4a. FrontISTR側のK（008、標準機能のみ版）
#    model/008_Tji_compare/FistrModel.cnt に !BOUNDARY + !TEMPERATURE + DUMPTYPE=MM + DUMPEXIT=YES
#    を書いて標準fistr1を1回実行 -> K_fistr_tji.mm にリネーム
# 4b. FrontISTR側のWdiff（--workdir でフォルダを切り替え）
python3 post/compute_kinvH_tji.py --workdir model/008_Tji_compare \
  --k K_fistr_tji.mm --h H_fistr_tji.npz --out Wdiff_fistr_tji.npy
python3 post/compute_kinvH_tji.py --workdir model/009_Tji_H_direct \
  --k K_fistr_tji.mm --h H_matrix.mtx --out Wdiff_fistr_tji.npy

# 5. ParaView用VTKを書き出す
python3 post/write_sensitivity_vtk.py --wdiff model/008_Tji_compare/Wdiff_python_tji.npy \
  --out model/008_Tji_compare/Wdiff_python_tji.vtk --field-name Sensitivity_Python
python3 post/write_sensitivity_vtk.py --wdiff model/008_Tji_compare/Wdiff_fistr_tji.npy \
  --out model/008_Tji_compare/Wdiff_fistr_tji.vtk --field-name Sensitivity_FrontISTR
python3 post/write_sensitivity_vtk.py --wdiff model/009_Tji_H_direct/Wdiff_fistr_tji.npy \
  --out model/009_Tji_H_direct/Wdiff_fistr_tji.vtk --field-name Sensitivity_FrontISTR_DUMPH
```

### どれとどれを比較しているか（フォルダ対応表）

| 量 | Python側 | FrontISTR側 | 比較スクリプト |
|---|---|---|---|
| H（生、境界条件なし） | `model/008_Tji_compare/H_python_tji.npz`（`python_H_tji.py`。同内容が`sample/002_thermalSensitive/Inp_Data/Results/H_python_tji.npz`にも） | `model/008_Tji_compare/H_fistr_tji.npz`（標準機能570回実行）**または**`model/009_Tji_H_direct/H_matrix.mtx`（DUMPH1回実行） | 手動で`scipy.sparse.load_npz`/`mmread`して比較（[`model/008_Tji_compare/README.md`](../model/008_Tji_compare/README.md)と[`model/009_Tji_H_direct/README.md`](../model/009_Tji_H_direct/README.md)に結果を記載） |
| K（境界条件適用後） | `model/008_Tji_compare/K_python_tji_bc.mtx` | `model/008_Tji_compare/K_fistr_tji.mm`（標準機能）／`model/009_Tji_H_direct/K_fistr_tji.mm`（DUMPH版と同時取得） | 同上 |
| Wdiff（節点19-103の相対変位感度） | `model/008_Tji_compare/Wdiff_python_tji.npy` | `model/008_Tji_compare/Wdiff_fistr_tji.npy`／`model/009_Tji_H_direct/Wdiff_fistr_tji.npy`（どちらも`compute_kinvH_tji.py`が計算） | 同上。ParaViewでの見た目比較は`*.vtk`（`docs/img/python_004FI_005FI.png`が実例） |

いずれも相対差1e-8〜1e-13（数値誤差レベル）で一致することを確認済み。
詳しい数値は[`model/008_Tji_compare/README.md`](../model/008_Tji_compare/README.md)と
[`model/009_Tji_H_direct/README.md`](../model/009_Tji_H_direct/README.md)を参照。

## 4. Tjiリファインメッシュ（22,123節点）用

対象モデル: `model/010_Tji_fine_H_direct`。570節点モデルの各四面体要素を8分割する
一様細分割（red refinement）を**2回繰り返し**（`--levels 2`）て22,123節点・108,736要素に
増やし、より大きい問題サイズでもPython実装とFrontISTR(DUMPH改造版)が一致するか、
計算時間がどう変わるかを確認する。標準機能で節点を1つずつ計算する方法は非現実的な時間に
なるため、このモデルではDUMPH改造版のみを使う。Wの求解も、節点数と同じ回数solveする方式
（`compute_kinvH_tji.py`）ではなく、**アジョイント法**（`wdiff_adjoint.py`、節点数によらず
6回のsolveで済む）に切り替えている（詳しい数式は`docs/12_...md`のセクション3参照）。

| スクリプト | 用途 | 主な入出力 |
|---|---|---|
| `refine_tji_mesh.py` | `Quad4_FEM_Tji.inp`の各C3D4要素を、各辺の中点を追加して8個の子要素に分割する（red refinement）。`--levels N`でN回繰り返す（既定1）。Fixed・Point_A・Point_Oは元の節点番号のまま引き継ぐ。 | 出力: `model/010_Tji_fine_H_direct/FistrModel.msh`, `hecmw_ctrl.dat`, `mesh_fine.npz`（Python計算用の中間形式）, `Quad4_FEM_Tji_fine.inp`（`ThermoSenseAnalyzer_00.py`用のAbaqus形式） |
| `python_H_tji_fine.py` | `mesh_fine.npz`を読み、`python_H_tji.py`と同じ数式でH・K（境界条件適用後）を組み立て、Wdiffはアジョイント法で計算する。`--young`/`--cte`で材料定数を上書きできる（`mesh_fine.npz`の既定値は元inpの値）。 | 出力: `model/010_Tji_fine_H_direct/H_python_tji_fine.npz`, `K_python_tji_fine_bc.mtx`, `Wdiff_python_tji_fine.npy` |
| `wdiff_adjoint.py` | FrontISTR側のK・Hから、アジョイント法でWdiffを計算する（`compute_kinvH_tji.py`の高速版）。Kが対称であることを使い、Point_A/Point_Oの6自由度分だけ`Kz=e`を解いてから`H`を1回掛ける。列数（節点数）に関係なく常に6回のsolveで済む。`--mesh-npz`でリファインメッシュにも対応。 | `--workdir <folder> --k <K.mtx> --h <H.mtx/npz> --out <Wdiff.npy> [--mesh-npz mesh_fine.npz]` |

`write_sensitivity_vtk.py`も`--mesh-npz mesh_fine.npz`を付ければそのままこのモデルにも
使える（3節参照）。

### リファインメッシュの実行手順

```bash
cd 20260810_KinvH

# 1. リファインメッシュを作る（2段リファイン、約0.1秒）
python3 post/refine_tji_mesh.py --levels 2

# 2. Python側でH・K・Wを計算（アジョイント法、4スレッドなら約210秒）
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 python3 post/python_H_tji_fine.py
#   材料定数を変えたい場合（例: ThermoSenseAnalyzer_00.pyのハードコード値に合わせる）:
#   python3 post/python_H_tji_fine.py --young 130000.0 --cte 1.0e-05

# 3. FrontISTR側でK・Hを1回の実行で同時取得（4スレッドで約92〜125秒）
cd model/010_Tji_fine_H_direct && OMP_NUM_THREADS=4 $HOME/local/frontistr-dumph/bin/fistr1 && \
  mv dump_matrix_1_0.mm K_fistr_tji_fine.mm && cd -

# 4. FrontISTR側のWdiff（アジョイント法、4スレッドで約59秒）
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 python3 post/wdiff_adjoint.py \
  --workdir model/010_Tji_fine_H_direct \
  --k K_fistr_tji_fine.mm --h H_matrix.mtx \
  --out Wdiff_fistr_tji_fine.npy --mesh-npz mesh_fine.npz

# 5. ParaView用VTKを書き出す
python3 post/write_sensitivity_vtk.py \
  --wdiff model/010_Tji_fine_H_direct/Wdiff_python_tji_fine.npy \
  --out   model/010_Tji_fine_H_direct/Wdiff_python_tji_fine.vtk \
  --field-name Sensitivity_Python --mesh-npz model/010_Tji_fine_H_direct/mesh_fine.npz
python3 post/write_sensitivity_vtk.py \
  --wdiff model/010_Tji_fine_H_direct/Wdiff_fistr_tji_fine.npy \
  --out   model/010_Tji_fine_H_direct/Wdiff_fistr_tji_fine.vtk \
  --field-name Sensitivity_FrontISTR --mesh-npz model/010_Tji_fine_H_direct/mesh_fine.npz

# 6. （参考）ThermoSenseAnalyzer_00.py自体を同じメッシュ・材料定数で実行して比較
cp model/010_Tji_fine_H_direct/Quad4_FEM_Tji_fine.inp sample/002_thermalSensitive/Inp_Data/
cd sample/002_thermalSensitive
python3 ThermoSenseAnalyzer_00_fixed.py Quad4_FEM_Tji_fine.inp 4   # 並列数=4プロセス
```

詳しい数値・計算時間は[`model/010_Tji_fine_H_direct/README.md`](../model/010_Tji_fine_H_direct/README.md)と
[`docs/12_手順_リファインメッシュでのK_H_W比較.md`](../docs/12_手順_リファインメッシュでのK_H_W比較.md)を参照。
