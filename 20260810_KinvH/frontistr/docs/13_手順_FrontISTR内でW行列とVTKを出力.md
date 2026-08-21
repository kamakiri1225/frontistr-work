# FrontISTRだけで感度行列WとVTKを出力する（DUMPWパッチ）

## 1. この手順で何をするか

これまでの流れでは、感度行列 $W$ の計算とVTK出力を**Python**（`post/wdiff_adjoint.py`、
`post/write_sensitivity_vtk.py`）で行っていた。FrontISTRからは $K$ と $H$ だけを取り出し、
そのあとPythonで $W = K^{-1}H$ を解いて可視化していた、ということである。

この手順では、その後半（ $W$ の計算とVTK出力）を**FrontISTRの中だけで完結**させる。
新しいキーワード `DUMPW=YES` を `!SOLVER` カードに付けると、`fistr1` を1回実行するだけで

- `sensitivity_Wdiff.vtk` … ParaViewでそのまま開ける感度場（ベクトル場）
- `Wdiff_fistr.txt` … `節点番号 wx wy wz` の素のテキスト（数値比較用）

の2つが出力される。**Pythonは不要**になる。

このためのパッチが `patch/frontistr_dumpw_tet.patch` である。
既存の `DUMPH` パッチ（ $H$ を出すだけ）とは**独立した別パッチ**で、
**別のソースフォルダ・別のビルドフォルダ・別のコマンド**で扱う。

### 1.1 適用範囲

- 四面体一次要素（`341`, C3D4）**および二次要素（`342`, C3D10）**
- 3次元ソリッド、1節点3自由度
- 線形静解析（`!SOLUTION,TYPE=STATIC`、非線形なし）
- 単一領域、MPIなし（複数領域だと異常終了する）
- `METHOD=DIRECT`（直接法。因子分解を使い回すため）

> このドキュメント（13）は一次要素（341）を中心に説明する。**二次要素（342）**への
> 対応と、`K`・`H`・`W`・`VTK` の4つを1回の実行で出力する使い方は
> `docs/14_手順_1次2次要素のW出力とvtk比較.md` にまとめてある。
> DUMPWは1回の実行で `sensitivity_Wdiff.vtk`・`Wdiff_fistr.txt` に加え
> `H_matrix.mtx`（ $H$ ）も出力する（`DUMPTYPE=MM` を併用すれば $K$ も同時に出る）。

---

## 2. 何を計算しているか（数式）

### 2.1 感度行列 W と Wdiff

$K$ を（境界条件適用後の）全体剛性行列、 $H$ を温度荷重変換行列とすると、
「節点温度を1つ動かしたときに各自由度がどれだけ動くか」を表す感度行列は次で定義される。

$$W = K^{-1} H$$

$K$ は $(3 n_{\text{node}}) \times (3 n_{\text{node}})$ 、 $H$ は $(3 n_{\text{node}}) \times n_{\text{node}}$ なので、
$W$ も $(3 n_{\text{node}}) \times n_{\text{node}}$ である。

実際に欲しいのは、**測定点A（Point_A）と基準点O（Point_O）の相対変位**が、
各節点温度でどう変わるか、である。これは $W$ から、Point_Aの3行とPoint_Oの3行を取り出して引き算した

$$W_{\text{diff}} = W[\text{Point A の3行}] - W[\text{Point O の3行}]$$

という ${3 \times n_{\text{node}}}$ の行列になる。

### 2.2 アジョイント（随伴）法：6回解くだけ

$W_{\text{diff}}$ を素直に作ると $W$ の全列（＝節点数だけの回数）を解く必要があり、節点数が
増えると非常に重い。そこで、 $K$ が対称であること（ $K^{-1}$ も対称）を使う。
$W_{\text{diff}}$ の各行は、Point_A / Point_O の6自由度に対応する単位ベクトル $e_i$ を使って

$$\text{row}_i = e_i^{\mathsf T} K^{-1} H = (K^{-1} e_i)^{\mathsf T} H = z_i^{\mathsf T} H$$

と書ける（ $z_i = K^{-1} e_i$ ）。つまり必要なのは **6本の $z_i$ を解くこと**だけで、
節点数がいくら増えても solve は6回で済む。詳しい導出は `docs/12` を参照。

### 2.3 FrontISTR内でどう実装したか

FrontISTRは変位を求めるとき、すでに $K$ を組み立てて因子分解（LU）している。
DUMPWはその**因子分解を使い回して**、6本の $z_i$ を**後退代入だけ**で解く。
そのあと、 $H$ をファイルに書かずに、要素ごとに標準ルーチン `TLOAD_C3` で
$H_e$ の列を計算し、その場で $z_i$ と掛けて $W_{\text{diff}}$ に足し込む
（ $H$ をメモリに丸ごと持たない）。

具体的には、 $g_c = z_{A,c} - z_{O,c}$ （ $c = x,y,z$ の3本）を作っておき、

$$W_{\text{diff}}[c, n] = g_c^{\mathsf T} H[:,n]$$

を要素ループの中で加算していく。

### 2.4 固定節点の扱い（重要）

固定された自由度は動けないので、その変位感度はゼロである。ところが直接法の
境界条件処理（対角を大きくする方式）では、**固定点そのものを測定点に選んだ場合**
（例：Point_Oが固定境界上にある場合）、 $z_i$ の固定自由度に見かけの値が残り、
その節点の列だけ $W_{\text{diff}}$ が異常に大きくなる。

そこでDUMPWは、6本の $z_i$ を解いたあと、**固定自由度の行を0にしてから** $g_c^{\mathsf T} H$ を
計算する。これはPython版（`post/wdiff_adjoint.py` の `Z[fixed_dof, :] = 0.0`）と同じ処理で、
固定自由度リストはFrontISTRの境界条件データ（`fstrSOLID%BOUNDARY_ngrp_*`）から
`fstr_AddBC` と同じ手順で作っている。

> この処理を入れる前は、`011_Tji_DUMPW`（Point_O=節点103は固定境界上）で
> 列103だけが `9.0e+04` などに発散した。固定自由度をゼロ化したら、後述のとおり
> Python結果と相対誤差 `2.4e-8` まで一致した。

---

## 3. パッチはどこを変更しているか

| ファイル | 変更内容 |
|---|---|
| `fistr1/src/common/fstr_ctrl_common.f90` | `!SOLVER` カードの新キーワード `DUMPW`（`NO`/`YES`）の読み取りを追加 |
| `fistr1/src/common/fstr_setup.f90` | 読み取った `DUMPW` を内部配列 `svIarray(37)` に格納する配線を追加 |
| `fistr1/src/lib/m_fstr.F90` | `Iarray(37)` の既定値を `0`（オフ）に初期化 |
| `fistr1/src/analysis/static/fstr_solve_NonLinear.f90` | 変位solveの直後に `fstr_dump_sensitivity` を追加。因子分解を使い回して6本の $z_i$ を解き、固定自由度をゼロ化して `export` へ渡す |
| `fistr1/src/analysis/static/fstr_ass_load.f90` | `fstr_sensitivity_read_dofs`（測定点の読み取り）、`fstr_sensitivity_export`（ $H$ 出力＋ $W_{\text{diff}} = g^{\mathsf T} H$ の加算、341/342対応）、`fstr_sensitivity_write_vtk`（VTK出力）を新規追加 |

---

## 4. ビルド手順（既存のFrontISTRとは別フォルダ）

既存の通常FrontISTRや `DUMPH` 版を壊さないよう、**別のソースフォルダ**を用意して
そこにDUMPWパッチを当て、**別のビルドフォルダ**でコンパイルする。ここではクリーンな
FrontISTRソースを `git worktree` で切り出す方法を使った（`$HOME/src/FrontISTR` が
FrontISTRのgitリポジトリである前提）。

```bash
# (1) クリーンなソースを別フォルダに切り出す（コミット 7f48eae0 = 5.9 相当）
cd $HOME/src/FrontISTR
git worktree add $HOME/src/FrontISTR-dumpw 7f48eae0

# (2) DUMPW改造を当てる —— 次の (2a) か (2b) のどちらか
cd $HOME/src/FrontISTR-dumpw
# (2a) パッチ（差分）を当てる
git apply /mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/frontistr/patch/frontistr_dumpw_tet.patch
# (2b) 改造ソースを元の位置にコピーして当てる（cp -r はマージ＝該当5ファイルだけ上書き、他は残る）
cp -r /mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/frontistr/patch/modified_src/fistr1 $HOME/src/FrontISTR-dumpw/

# (3) 別ビルドフォルダ build-dumpw で設定する（DUMPHのときと同じオプション）
cmake -S . -B build-dumpw \
  -DCMAKE_BUILD_TYPE=RELEASE \
  -DCMAKE_INSTALL_PREFIX=$HOME/src/FrontISTR-dumpw/install \
  -DWITH_MPI=OFF -DWITH_OPENMP=ON -DWITH_LAPACK=ON \
  -DWITH_MKL=OFF -DWITH_MUMPS=OFF -DWITH_METIS=OFF \
  -DWITH_NETCDF=OFF -DWITH_REFINER=OFF -DWITH_REVOCAP=OFF \
  -DWITH_TOOLS=OFF -DWITH_DOC=OFF

# (4) コンパイル
cmake --build build-dumpw -j4
```

最後に `[100%] Built target fistr1` が出れば成功。改造版の実行ファイルは次にできる。

```text
$HOME/src/FrontISTR-dumpw/build-dumpw/fistr1/fistr1
```

> `git worktree` を使わない場合は、`git clone` や `cp -r` でソースを別フォルダに複製し、
> そこにパッチを当ててもよい。要は「通常版とは別のソース・別のビルド先」であればよい。

---

## 5. 実行手順（`model/011_Tji_DUMPW` の例）

### 5.1 入力ファイル

`model/011_Tji_DUMPW/` に次を置く。

| ファイル | 役割 |
|---|---|
| `FistrModel.msh` | メッシュ（570節点のQuad4_FEM_Tji、`009` からコピー） |
| `hecmw_ctrl.dat` | FrontISTRの入出力設定 |
| `FistrModel.cnt` | 解析条件。`!SOLVER` に `DUMPW=YES` を付ける |
| `sensitivity_points.dat` | **Point_A と Point_O のグローバル節点番号を1行**（この例は `19 103`） |

`FistrModel.cnt` の要点は次のとおり。

```text
!SOLVER,METHOD=DIRECT,ITERLOG=NO,TIMELOG=YES,DUMPW=YES
```

- `METHOD=DIRECT` … 直接法。因子分解を6回の後退代入で使い回すために必要。
- `DUMPW=YES` … 感度行列WとVTKを出力する。
- `DUMPEXIT=YES` は**付けない**。DUMPWは実際に変位を解いて因子分解を作る必要があるため。
- 測定点は `.cnt` ではなく `sensitivity_points.dat` で指定する（`19 103` のように空白区切りで2つ）。

`sensitivity_points.dat` の中身（この例）：

```text
#Point_A, Point_O
19 103
```

`#` や `!` で始まる行はコメント。**このファイルが無い／読めないと、DUMPWはエラーで停止する**
（終了コード非0）。そのとき `FSTR.msg` と標準出力に、必要なファイル名と書き方の例が出る。

```text
DUMPW ERROR: cannot find/open "sensitivity_points.dat".
DUMPW: the file "sensitivity_points.dat" is REQUIRED in the run directory.
       Write ONE line with two global node ids: <Point_A> <Point_O>
       (# or ! start a comment line). Example:
         #Point_A, Point_O
         19 103
```

### 5.2 実行

```bash
cd /mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/frontistr/model/011_Tji_DUMPW
$HOME/src/FrontISTR-dumpw/build-dumpw/fistr1/fistr1 > run_dumpw.log 2>&1
```

`FSTR.msg` に次のようなメッセージが出れば成功。

```text
DUMPW: Point_A global 19 -> local 19
DUMPW: Point_O global 103 -> local 103
DUMPW: wrote H_matrix.mtx, sensitivity_Wdiff.vtk, Wdiff_fistr.txt; n_node= 570  n_elem_solid= 1699
```

### 5.3 出力ファイル

| ファイル | 内容 | 使い方 |
|---|---|---|
| `sensitivity_Wdiff.vtk` | 感度場 $W_{\text{diff}}$ （ベクトル場 `Sensitivity`） | ParaViewで開いてGlyphやWarp、色分け表示 |
| `Wdiff_fistr.txt` | `# global_node_id  Wdiff_x  Wdiff_y  Wdiff_z` の表 | Excelやスクリプトで数値確認・比較 |

`sensitivity_Wdiff.vtk` はレガシーASCII形式のUnstructured Grid（VTK_TETRA）で、
`post/write_sensitivity_vtk.py` がPythonで書いていたものと同じ体裁である。

---

## 6. 検証結果（Python版との一致）

`011_Tji_DUMPW`（FrontISTR内部計算）の `Wdiff_fistr.txt` を、`009_Tji_H_direct` の
Python版アジョイント結果 `Wdiff_fistr_tji.npy`（`post/wdiff_adjoint.py` が $K$ と $H$ から
計算したもの）と突き合わせた。材料定数は両者そろえてある（ヤング率 `130000000.0`、
ポアソン比 `0.27`、線膨張係数 `1.2e-5`。なお $W$ は線膨張係数に比例しヤング率には依存しない）。

| 比較項目 | 値 |
|---|---|
| 相対差 $\lVert W^{\text{fistr}}_{\text{diff}} - W^{\text{py}}_{\text{diff}} \rVert / \lVert W^{\text{py}}_{\text{diff}} \rVert$ | `2.4e-8` |
| 要素ごとの最大絶対差 | `1.2e-11` |
| Point_O(節点103, 固定)の列 | fistr `[1.007e-4, -8.88e-7, 7.10e-5]` ／ py `[1.007e-4, -8.88e-7, 7.10e-5]` |

相対差 `2.4e-8` は倍精度の丸め誤差レベルであり、**FrontISTR内部計算とPython版は実質一致**した。
（Python側の `ThermoSenseAnalyzer_00.py` はfloat32のため別途11%程度ずれるが、これは
`docs/12` で説明済みの単精度の問題で、DUMPWの正しさとは別の話である。）

### 6.1 計算コスト

`011`（570節点）の実測では、`fistr1` 全体で約 `0.18` 秒。内訳を見ると、変位を解くための
最初の因子分解のあと、DUMPWの6本の $z_i$ は**各回およそ 0.1 ミリ秒の後退代入**で終わっている。
これは「因子分解を1回作って、あとは6回の後退代入だけ」という2.3節の設計どおりで、
節点数が増えても solve 回数は6回のまま増えない。

---

## 7. どのフォルダのどれを見ればよいか

| 見たいもの | 場所 |
|---|---|
| DUMPWパッチ本体 | `patch/frontistr_dumpw_tet.patch` |
| パッチの日本語解説 | `patch/README.md`（`DUMPW` の節） |
| 実行用の入力一式 | `model/011_Tji_DUMPW/`（`FistrModel.cnt` / `hecmw_ctrl.dat` / `sensitivity_points.dat`） |
| FrontISTR内部の出力 | `model/011_Tji_DUMPW/sensitivity_Wdiff.vtk`, `Wdiff_fistr.txt` |
| 比較したPython版の結果 | `model/009_Tji_H_direct/Wdiff_fistr_tji.npy` |
| アジョイント法の詳しい数式 | `docs/12_手順_リファインメッシュでのK_H_W比較.md` |

---

## 8. DUMPH との違い（まとめ）

| | DUMPH（既存） | DUMPW（この手順） |
|---|---|---|
| キーワード | `!SOLVER,...,DUMPH=YES` | `!SOLVER,...,DUMPW=YES` |
| 出力 | `H_matrix.mtx`（ $H$ そのもの） | `sensitivity_Wdiff.vtk` + `Wdiff_fistr.txt`（ $W_{\text{diff}}$ ） |
| solveするか | しない（`DUMPEXIT=YES` で即終了） | する（因子分解を作り、6本の $z_i$ を後退代入） |
| その後のPython | 必要（ $W$ 計算＋VTK） | **不要**（FrontISTR内で完結） |
| パッチ | `frontistr_dumph_341.patch` | `frontistr_dumpw_tet.patch`（独立） |
| ビルド先 | 通常の改造版ビルド | 別フォルダ `build-dumpw` |
