# 010_Tji_fine_H_direct

## 目的

`model/008_Tji_compare` / `009_Tji_H_direct`（570節点）よりも大きい問題サイズで、
PythonとFrontISTR(DUMPH改造版)のK・H・Wが一致するか、また計算時間がどう変わるかを
確認する。`post/refine_tji_mesh.py`で、元の`Quad4_FEM_Tji.inp`（570節点・1699要素、
ファイル自体は一切変更しない）の各四面体要素を8分割する一様細分割（red refinement、
各辺に中点を追加）を**2回繰り返し**（`--levels 2`）、**22,123節点・108,736要素**の
メッシュを作った。Fixed節点・Point_A(19)・Point_O(103)は元の節点番号のまま
（座標も変わらない）なので、そのまま引き継いでいる。

## リファイン方法

各四面体を6辺の中点で8個の子四面体に分割する（1段で8倍、2段で64倍の要素数）。
共有辺の中点は`(節点id_a, 節点id_b)`の組をキーにした辞書で重複なく1つにまとめている。
詳細は`post/refine_tji_mesh.py`を参照。

```bash
python3 post/refine_tji_mesh.py --levels 2
# -> FistrModel.msh, hecmw_ctrl.dat, mesh_fine.npz, Quad4_FEM_Tji_fine.inp
```

| | 元メッシュ | 1段リファイン | 2段リファイン（このフォルダ） |
|---|---|---|---|
| 節点数 | 570 | 3,314 | **22,123** |
| 要素数 | 1,699 | 13,592 | **108,736** |
| 自由度(DOF_TOTAL) | 1,710 | 9,942 | **66,369** |

## FrontISTR側: K・Hを1回の実行で両方取得

`docs/11_...md`で確認した通り、`!BOUNDARY`(RHSを非ゼロにする)＋`!TEMPERATURE`＋
`DUMPH=YES`＋`DUMPTYPE=MM`＋`DUMPEXIT=YES`を組み合わせると、**1回の実行**で
境界条件適用後のK(`dump_matrix_1_0.mm`)とHの生値(`H_matrix.mtx`)が同時に出力される。
このフォルダではこの方式を使った（K専用・H専用で2回実行する必要がない）。

```bash
cd model/010_Tji_fine_H_direct
$HOME/local/frontistr-dumph/bin/fistr1
mv dump_matrix_1_0.mm K_fistr_tji_fine.mm
```

実行時間: **98.57 s**（22123節点・108736要素、`/usr/bin/time`で計測。並列数はOpenMPが
自動検出した48スレッド、明示的な制限はしていない）。

## Python側: リファインメッシュでK・H・Wを計算

`post/python_H_tji_fine.py`が`mesh_fine.npz`を読み、`python_H_tji.py`と同じ数式で
K・Hを組み立てる。Wの求解は**アジョイント法**（`docs/12_...md`参照、Point_A/Point_Oの
6自由度だけ解く方式）に切り替えている。シングルプロセス実行（並列数1、
`OMP_NUM_THREADS`等は未設定＝環境既定値）。

```bash
python3 post/python_H_tji_fine.py
```

内訳（`/usr/bin/time`で計測、real=208.01 s）:

| フェーズ | 時間 |
|---|---|
| K・H要素ループ組み立て | 34.503 s |
| H保存(npz) | 0.494 s |
| 境界条件処理(K・H) | 111.391 s |
| W = K⁻¹H 求解（アジョイント法、6回） | 18.820 s |
| Z^T H（疎×密 行列積） | 0.006 s |
| 合計(内部計測) | 205.581 s |

境界条件処理が111秒と大きいのは、固定自由度の行・列を`lil`形式で1つずつゼロ化する
実装が自由度数（66369）に対して効率的でないため（改善余地あり、今回は未対応）。

## W = K⁻¹H（FrontISTR側）

FrontISTR自体はWを計算しないので、FrontISTR側のK・Hを読み込んで
**アジョイント法**（`post/wdiff_adjoint.py`）で計算する。22123節点では、
列ごとに全部解く`compute_kinvH_tji.py`（1段リファイン=3314節点までは使っていた方式）は
非現実的な時間がかかるため使っていない。シングルプロセス実行（並列数1）。

```bash
python3 post/wdiff_adjoint.py \
  --workdir model/010_Tji_fine_H_direct \
  --k K_fistr_tji_fine.mm --h H_matrix.mtx \
  --out Wdiff_fistr_tji_fine.npy --mesh-npz mesh_fine.npz
```

実行時間: 読込40.519 s + アジョイント求解(6回)19.675 s + 行列積0.005 s =
**60.387 s**（real 60.92 s）。

## 比較結果

| 項目 | 最大絶対差 | 相対差(Frobenius) |
|---|---|---|
| H（生、境界条件なし） | 1.954e-07 | 8.749e-13 |
| K（境界条件適用後） | 5.001e-03 | 1.382e-12 |
| Wdiff（節点19-103の感度、アジョイント法） | 6.929e-10 | 9.920e-08 |

570節点・3314節点モデルと同様、いずれも数値誤差レベルで一致した。問題サイズを
約39倍（節点数570→22123、要素数1699→108736）に増やしても、Python実装と
FrontISTR(DUMPH改造版)は一致し続ける。

## トータル計算時間

| 経路 | 内訳 | トータル |
|---|---|---|
| Python（`python_H_tji_fine.py`1本、アジョイント法） | K・H組立+保存+BC+アジョイントW求解を一括 | **205.58 s** |
| FrontISTR + DUMPH改造版 | K+H同時出力98.57 s + アジョイントW計算60.92 s | **159.49 s** |

570節点（Python 3.01s、FrontISTR+DUMPH 3.63s）・3314節点（Python 39.61s、
FrontISTR+DUMPH 44.18s）のときはPythonがわずかに速かったが、22123節点では
**FrontISTR側の方が速く**なった（159.49s vs 205.58s）。これはPython側の境界条件処理
（111秒、`lil`形式の非効率な実装）が支配的になっているためで、W計算自体
（アジョイント法6回）はPython 18.8秒・FrontISTR 19.7秒とほぼ同じ。

アジョイント法へ切り替える前の「列ごとに全部solve」方式のままだと、W計算だけで
（3314節点で24秒だった実績の伸び方から）数十分かかっていたと見込まれる。
アジョイント法により、W計算は節点数を5.8倍→6.7倍に増やしてもほぼ19秒のまま
頭打ちになった。詳しい考察は`docs/12_...md`を参照。

標準機能だけでHを節点を1つずつ計算してH取得する方式（22123回`fistr1`を再実行する）は
非現実的な時間になるため、今回は実行していない。

## ThermoSenseAnalyzer_00.py（実機）でのこのメッシュでの実行

`sample/002_thermalSensitive/Inp_Data/Quad4_FEM_Tji_fine.inp`
（`refine_tji_mesh.py`が出力したAbaqus形式）を、構文修正版
`ThermoSenseAnalyzer_00_fixed.py`（`docs/11_...md`参照）で実行して比較する。

```bash
cd sample/002_thermalSensitive
python3 ThermoSenseAnalyzer_00_fixed.py Quad4_FEM_Tji_fine.inp 8   # 並列数=8プロセス
```

（結果は別途追記予定）

## ParaViewで見るもの

`Wdiff_python_tji_fine.vtk` / `Wdiff_fistr_tji_fine.vtk`（どちらも22123節点・108736要素、
1ファイル約5.6MB）。`.gitignore`対象外だが、570節点モデルの約97KBや3314節点モデルの
約680KBよりかなり重いので、pushする際はサイズに注意。`H_matrix.mtx`（約169MB）・
`K_fistr_tji_fine.mm`（約88MB）は`.gitignore`の`*.mtx`/`*.mm`ルールで除外される
（サイズ的にもpushすべきではない）。
