# FrontISTRに温度荷重行列Hの出力機能を追加する

## 1. この手順で行うこと

FrontISTR 5.9へ次の入力設定を追加し、温度荷重行列Hを1回の解析で出力する。

```text
!SOLVER,METHOD=DIRECT,DUMPTYPE=MM,DUMPH=YES,DUMPEXIT=YES
```

出力ファイルは `H_matrix.mtx`。Matrix Market形式の疎行列である。

この実装は検証の第一段階として、次の条件に限定している。

- 四面体一次要素（FrontISTR要素タイプ341）
- 3次元ソリッド、1節点3自由度
- 線形静解析
- 単一領域、MPIなし
- 弾性係数と線膨張係数が温度に依存しない

### 1.1 何を使ってコンパイルしたか

今回、改造版FrontISTRのコンパイルに実際に使用した環境は次のとおり。

| 項目 | 使用したもの |
|---|---|
| OS環境 | Ubuntu 24.04.3 LTSを動かしたWSL2、x86_64 |
| FrontISTR | FrontISTR 5.9、Gitコミット `7f48eae0` |
| ビルド設定 | CMake 3.28.3 |
| Fortranコンパイラ | GNU Fortran 13.3.0 |
| Cコンパイラ | GCC 13.3.0 |
| C++コンパイラ | G++ 13.3.0 |
| ビルド種別 | `RELEASE` |
| 並列機能 | MPI無効、OpenMP有効 |
| 数値ライブラリ | LAPACK有効、MKLとMUMPSは無効 |

FrontISTRの大部分はFortranで書かれているため、主となるコンパイラは
GNU Fortran、一般に `gfortran` と呼ばれるコンパイラである。

今回CMakeが使用したFortranコンパイラのパスは次のとおり。

```text
/usr/bin/f95
```

この環境では `/usr/bin/f95` の実体は次のGNU Fortran 13である。

```text
/usr/bin/x86_64-linux-gnu-gfortran-13
```

`f95` という名前から別製品のコンパイラに見えるが、この環境では
GNU Fortranを指すシンボリックリンクである。

FrontISTRにはCとC++で書かれた部分もあるため、CMakeは次のコンパイラも使用した。

```text
C compiler:   /usr/bin/cc  -> GCC 13.3.0
C++ compiler: /usr/bin/c++ -> G++ 13.3.0
```

自分の環境で同じ情報を確認するコマンドは次のとおり。

```bash
gfortran --version | head -n 1
gcc --version | head -n 1
g++ --version | head -n 1
cmake --version | head -n 1
readlink -f /usr/bin/f95
```

各コマンドの意味は次のとおり。

| コマンド | 確認内容 |
|---|---|
| `gfortran --version` | GNU Fortranのバージョン |
| `gcc --version` | GNU Cコンパイラのバージョン |
| `g++ --version` | GNU C++コンパイラのバージョン |
| `cmake --version` | CMakeのバージョン |
| `head -n 1` | バージョン表示の先頭1行だけを表示する |
| `readlink -f /usr/bin/f95` | `/usr/bin/f95` が最終的に指す実ファイルを表示する |

### 1.2 実際に成功したビルド

通常利用しているFrontISTRを壊さないよう、最初の検証ではソースを
`/tmp` の一時フォルダへ複製した。

```text
/tmp/frontistr-hsrc.1Rzr0X
```

改造したソースはこの一時フォルダにあり、ビルド結果は次へ生成した。

```text
/tmp/frontistr-hsrc.1Rzr0X/build-h
```

実際に成功したCMake設定コマンドは次のとおり。

```bash
cd /tmp/frontistr-hsrc.1Rzr0X

cmake -S . -B build-h \
  -DCMAKE_BUILD_TYPE=RELEASE \
  -DCMAKE_INSTALL_PREFIX=/tmp/frontistr-hsrc.1Rzr0X/install \
  -DWITH_MPI=OFF \
  -DWITH_OPENMP=ON \
  -DWITH_LAPACK=ON \
  -DWITH_MKL=OFF \
  -DWITH_MUMPS=OFF \
  -DWITH_METIS=OFF \
  -DWITH_NETCDF=OFF \
  -DWITH_REFINER=OFF \
  -DWITH_REVOCAP=OFF \
  -DWITH_TOOLS=OFF \
  -DWITH_DOC=OFF
```

このコマンドでは、コンパイル用ファイルを `build-h` に作成した。
まだFrontISTR本体はコンパイルしていない。

続いて、次のコマンドでコンパイルした。

```bash
cmake --build build-h -j2
```

ビルドの最後に次の表示を確認した。

```text
[100%] Built target fistr1
```

この表示は、FrontISTRの実行ファイル `fistr1` のリンクまで成功したことを示す。

実際に生成された改造版実行ファイルは次の場所にある。

```text
/tmp/frontistr-hsrc.1Rzr0X/build-h/fistr1/fistr1
```

この実行ファイルを使い、次の解析フォルダでHを出力した。

```text
/mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/frontistr/model/005_H_direct
```

実行コマンドは次のとおり。

```bash
cd /mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/frontistr/model/005_H_direct
/tmp/frontistr-hsrc.1Rzr0X/build-h/fistr1/fistr1 > run_dumph.log 2>&1
```

終了コードは0で、`H_matrix.mtx` の出力に成功した。
`FSTR.msg` にも次のメッセージが記録された。

```text
DUMPH: wrote H_matrix.mtx, shape=1275 425
```

### 1.3 実施済みと再現用手順の区別

今回、実際に確認した範囲は次のとおり。

- `/tmp` のソースコピーへのDUMPH実装
- CMakeによるビルド設定
- `cmake --build build-h -j2` によるコンパイル
- 生成された改造版 `fistr1` の実行
- `H_matrix.mtx`、K、RHSの出力
- Hの第2列と標準温度荷重RHSの一致

一方、`$HOME/local/frontistr-dumph` へのインストールは、
恒久的に使うための再現手順として第6章に記載しているが、まだ実施していない。
したがって、第6章のインストール先に実行ファイルが存在するとは限らない。

## 2. 物理的に計算しているもの

### 2.1 温度から熱ひずみへの変換

等方材料の熱ひずみは、温度差を $\Delta T$、線膨張係数を $\alpha$ とすると次式になる。

$$
\boldsymbol{\varepsilon}_{\mathrm{th}} = \alpha \Delta T \begin{bmatrix} 1 & 1 & 1 & 0 & 0 & 0 \end{bmatrix}^{\mathsf T}
$$

要素内部の温度は、節点温度 $\boldsymbol{T}_e$ と形状関数 $\boldsymbol{N}$ から補間する。

$$
T(\boldsymbol{\xi})=\boldsymbol{N}(\boldsymbol{\xi})\boldsymbol{T}_e
$$

### 2.2 熱ひずみから節点熱荷重への変換

要素の等価熱荷重ベクトルは次式で計算する。

$$
\boldsymbol{f}_{\mathrm{th},e} = \int_{V_e} \boldsymbol{B}^{\mathsf T} \boldsymbol{D} \boldsymbol{\varepsilon}_{\mathrm{th}} \,\mathrm{d}V
$$

温度に依存する部分を節点温度の前へまとめると、次の形になる。

$$
\boldsymbol{f}_{\mathrm{th},e} = \boldsymbol{H}_e\boldsymbol{T}_e
$$

$$
\boldsymbol{H}_e = \int_{V_e} \boldsymbol{B}^{\mathsf T} \boldsymbol{D} \alpha \begin{bmatrix} 1 & 1 & 1 & 0 & 0 & 0 \end{bmatrix}^{\mathsf T} \boldsymbol{N} \,\mathrm{d}V
$$

ここで、$\boldsymbol{B}$ は変位・ひずみ行列、$\boldsymbol{D}$ は弾性構成則行列である。

### 2.3 ソースコードでの求め方

FrontISTRの既存ルーチン `TLOAD_C3` は、節点温度から要素熱荷重ベクトルを計算する。

今回の改造では、四面体要素の局所節点 $j$ だけを1、他を0とした単位温度ベクトル $\boldsymbol{e}_j$ を順に与える。

$$
\boldsymbol{H}_e\boldsymbol{e}_j = \boldsymbol{H}_e[:,j]
$$

これにより、既存の `TLOAD_C3` を使って要素Hの各列を求める。得られた要素Hを全要素について出力し、同じ全体行・列の成分を加算すると全体Hになる。

独自の有限要素式を別に実装せず、FrontISTRが実際に温度荷重を計算するルーチンを再利用している点が重要である。

## 3. フォルダ構成

今回関係するフォルダは次のとおり。

```text
$HOME/src/FrontISTR/                 FrontISTR標準ソース
├── fistr1/src/analysis/static/
│   └── fstr_ass_load.f90                     温度荷重計算とH出力処理
├── fistr1/src/common/
│   ├── fstr_ctrl_common.f90                  DUMPHキーワードの読み取り
│   └── fstr_setup.f90                        DUMPH設定の受け渡し
└── fistr1/src/lib/
    └── m_fstr.F90                            DUMPHの既定値

/mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/
├── patch/
│   └── frontistr_dumph_341.patch             検証済みソース差分
├── model/
│   ├── 003_Htest/                            節点2の単位温度による検証
│   └── 005_H_direct/                         DUMPH実行用入力一式
└── docs/
    ├── 03_温度荷重行列H_FrontISTR標準機能調査.md
    ├── 04_手順_温度荷重行列H_FrontISTR.md
    ├── 05_手順_FrontISTR_DUMPH追加とビルド.md
    └── 07_WORK_LOG.md
```

## 4. ソースコードのどこを変更したか

### 4.1 変更全体の流れ

追加した処理は、次の順番で動く。

```text
FistrModel.cnt の DUMPH=YES
  ↓
fstr_ctrl_common.f90 が文字列を読み取る
  ↓
fstr_setup.f90 が設定値を svIarray(36) へ保存する
  ↓
m_fstr.F90 で既定値をOFFにしておく
  ↓
fstr_ass_load.f90 が svIarray(36) を確認する
  ↓
要素タイプ341の要素Hを計算する
  ↓
H_matrix.mtx を出力する
```

`svIarray` は、FrontISTRのソルバー設定を整数で保持する配列である。
今回未使用だった36番をDUMPHの保存場所として使用した。

### 4.2 `fstr_ctrl_common.f90`：DUMPHを読み取る

ファイルの場所は次のとおり。

```text
$HOME/src/FrontISTR/fistr1/src/common/fstr_ctrl_common.f90
```

このファイルにある `fstr_ctrl_get_SOLVER` は、`!SOLVER` 行を解析する関数である。

最初に、関数の引数へ `dumph` を追加した。

```fortran
function fstr_ctrl_get_SOLVER(..., dumptype, dumpexit, dumph, usejad, ...)
```

次に、`DUMPH=NO` と `DUMPH=YES` を読み取る処理を追加した。

```fortran
if (fstr_ctrl_get_param_ex( &
    ctrl, 'DUMPH ', 'NO,YES ', 0, 'P', dmph) /= 0) return
```

内部では、入力値を一時変数 `dmph` で受け取り、最後に0または1へ変換する。

```fortran
dmph = dumph + 1
...
dumph = dmph - 1
```

変換後の値は次の意味になる。

| 入力 | 内部値 |
|---|---:|
| `DUMPH=NO` または指定なし | `0` |
| `DUMPH=YES` | `1` |

この変更によって、未改造FrontISTRでは未知のパラメータだった `DUMPH` を、
`!SOLVER` の正式な入力値として読み取れるようになる。

### 4.3 `fstr_setup.f90`：設定値を解析処理へ渡す

ファイルの場所は次のとおり。

```text
$HOME/src/FrontISTR/fistr1/src/common/fstr_setup.f90
```

`fstr_setup_SOLVER` は、読み取ったソルバー設定をFrontISTR内部の配列へ保存する。

既存の `fstr_ctrl_get_SOLVER` 呼び出しへ `svIarray(36)` を追加した。

```fortran
rcode = fstr_ctrl_get_SOLVER( &
  ...,
  svIarray(31),  & ! DUMPTYPE
  svIarray(32),  & ! DUMPEXIT
  svIarray(36),  & ! DUMPH: 今回追加
  svIarray(33),  & ! USEJAD
  ...)
```

これによって、`DUMPH=YES` は次の状態で解析処理まで渡される。

```text
svIarray(36) = 1
```

`DUMPH=NO` または指定なしの場合は0になる。

### 4.4 `m_fstr.F90`：DUMPHの既定値をOFFにする

ファイルの場所は次のとおり。

```text
$HOME/src/FrontISTR/fistr1/src/lib/m_fstr.F90
```

行列・ソルバー設定を初期化する `fstr_mat_init` に、次の1行を追加した。

```fortran
hecMAT%Iarray(36) = 0  ! dump thermal load matrix H
```

この0は `DUMPH=NO` を表す。

既定値をOFFにした理由は、通常のFrontISTR解析へ影響を与えないためである。
`DUMPH` を書かなければH出力処理は動かず、従来どおりに解析する。

### 4.5 `fstr_ass_load.f90`：Hを計算して出力する

ファイルの場所は次のとおり。

```text
$HOME/src/FrontISTR/fistr1/src/analysis/static/fstr_ass_load.f90
```

このファイルは、集中荷重、分布荷重、温度荷重などを全体RHSへ組み立てる。
今回の中心となる変更はこのファイルにある。

#### Hを1回だけ出力するためのフラグ

静解析では荷重組み立て処理が複数回呼ばれる場合がある。
同じHを何度も出力しないよう、モジュール内へ次のフラグを追加した。

```fortran
logical, save :: thermal_matrix_exported = .false.
```

- `.false.`：まだHを出力していない
- `.true.`：すでにHを出力した
- `save`：サブルーチンを抜けても値を保持する

#### DUMPHがONの場合だけ出力する

標準の温度荷重処理 `process_thermal_loads` の直後へ、次の条件分岐を追加した。

```fortran
call process_thermal_loads(cstep, ctime, hecMESH, hecMAT, fstrSOLID)

if (svIarray(36) /= 0 .and. .not. thermal_matrix_exported) then
  call export_thermal_matrix_341(hecMESH, fstrSOLID)
  thermal_matrix_exported = .true.
endif
```

条件は次の2つである。

- `svIarray(36) /= 0`：入力に `DUMPH=YES` がある
- `.not. thermal_matrix_exported`：まだHを出力していない

両方を満たすときだけ、新しく追加した `export_thermal_matrix_341` を呼ぶ。

#### 追加した `export_thermal_matrix_341`

このサブルーチンが、要素タイプ341のHを `H_matrix.mtx` へ出力する。

処理の順番は次のとおり。

1. MPI領域数が1であることを確認する
2. 要素タイプ341の有効要素数を数える
3. `H_matrix.mtx` を開き、Matrix Marketヘッダーを書く
4. 全要素を順番に処理する
5. 要素を構成する4節点の座標と全体節点番号を取得する
6. 局所節点1～4へ順番に単位温度を与える
7. 既存の `TLOAD_C3` で要素温度荷重を計算する
8. 計算結果を全体自由度行・全体温度列としてファイルへ書く

単位温度を作る部分は次のコードである。

```fortran
do k = 1, nn
  tt(:) = 0.0d0
  tt(k) = 1.0d0

  call TLOAD_C3( &
    etype, nn, xx, yy, zz, tt, tt0, &
    fstrSOLID%elements(icel)%gausses, &
    vect, cdsys_ID, coords)
  ...
enddo
```

四面体一次要素では `nn=4` なので、`k=1` から `k=4` まで処理する。

例えば `k=2` の場合、要素節点温度は次の状態になる。

```text
tt = [0, 1, 0, 0]
```

このとき `TLOAD_C3` が返す `vect` は、要素Hの第2列になる。

$$
\boldsymbol H_e\boldsymbol e_2 = \boldsymbol H_e[:,2]
$$

#### 全体行番号と列番号

要素内の荷重成分を、全体行列Hの行番号へ変換する式は次の部分である。

```fortran
ndof*(nodLocal(j)-1)+i
```

- `nodLocal(j)`：要素の局所節点に対応する全体節点番号
- `ndof=3`：1節点あたりx、y、zの3自由度
- `i=1,2,3`：x、y、z方向

列番号には、単位温度を与えた全体節点番号 `nodLocal(k)` を使用する。

```fortran
write(iunit, ...) &
  ndof*(nodLocal(j)-1)+i, & ! Hの全体行番号
  nodLocal(k),             & ! Hの全体列番号
  vect(ndof*(j-1)+i)         ! Hの値
```

### 4.6 変更していない重要なファイル

温度荷重の計算式がある次のファイルは変更していない。

```text
$HOME/src/FrontISTR/fistr1/src/lib/static_LIB_3d.f90
```

この中の既存ルーチン `TLOAD_C3` を、そのままHの各列計算に使用した。

つまり、熱ひずみやガウス積分を別の式で作り直したのではない。
FrontISTR標準の温度荷重計算を呼び出し、入力温度だけを単位ベクトルへ
切り替えてHの列を取得している。

### 4.7 パッチで変更されるファイル一覧

#### `fistr1/src/common/fstr_ctrl_common.f90`

- `!SOLVER` に `DUMPH=NO/YES` を追加する
- 入力値を整数フラグへ変換する

#### `fistr1/src/common/fstr_setup.f90`

- `DUMPH` の値を `svIarray(36)` へ格納する

#### `fistr1/src/lib/m_fstr.F90`

- `DUMPH` の既定値を0、つまりOFFにする
- 指定しない通常解析の動作は変わらない

#### `fistr1/src/analysis/static/fstr_ass_load.f90`

- `DUMPH=YES` の場合だけHを出力する
- 要素タイプ341の各節点へ単位温度を与え、`TLOAD_C3` で要素Hの列を計算する
- `H_matrix.mtx` を出力する
- 静解析中に複数回呼ばれても、Hの出力は最初の1回だけにする

## 5. パッチを適用する

最初にFrontISTRソースの状態を確認する。

```bash
cd $HOME/src/FrontISTR
git status --short
git rev-parse --short HEAD
```

各コマンドの意味は次のとおり。

| コマンド | 意味 |
|---|---|
| `cd $HOME/src/FrontISTR` | 作業場所をFrontISTRのソース最上位フォルダへ移動する。パッチ内のファイルパスは、この場所を基準にしている |
| `git status --short` | 変更済みファイルと未追跡ファイルを短い形式で表示する。パッチ適用前の状態を記録するために使う |
| `git rev-parse --short HEAD` | 現在チェックアウトしているGitコミットを短いIDで表示する |

`git status --short` の先頭記号は、主に次の意味を持つ。

| 表示 | 意味 |
|---|---|
| `M ファイル名` | Gitで管理されているファイルが変更されている |
| `?? ファイル名` | Gitでまだ管理されていないファイルやフォルダがある |
| 何も表示されない | Gitで管理されている作業ツリーに変更がない |

今回変更する4ファイルに、すでに `M` が付いている場合は注意する。
先に入っている変更とパッチが重なる可能性があるため、内容を確認してから進める。

このパッチを検証したコミットは `7f48eae0`。別のコミットへ適用する場合は、差分の衝突と周辺コードを確認する。

パッチが適用できるか、ファイルを書き換えずに確認する。

```bash
git apply --check \
  /mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/frontistr/patch/frontistr_dumph_341.patch
```

このコマンドの意味は次のとおり。

- `git apply`：Git形式の差分ファイルを作業ツリーへ適用するコマンド
- `--check`：実際にはファイルを書き換えず、適用可能かだけを確認する
- 行末の `\`：シェルコマンドが次の行へ続くことを示す
- 最後のパス：適用可否を確認するパッチファイル

成功した場合は、通常何も表示されず、コマンドが終了する。
この時点ではソースファイルは変更されない。

`patch does not apply` などのエラーが出た場合は、ソースのバージョンが違うか、
対象ファイルに別の変更が入っている可能性がある。エラーを無視して次へ進めない。

エラーが出なければ適用する。

```bash
git apply \
  /mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/frontistr/patch/frontistr_dumph_341.patch
```

`--check` を外したため、このコマンドは実際に4つのソースファイルを変更する。

注意点は次のとおり。

- Gitコミットは作成しない
- ブランチを切り替えない
- FrontISTRをまだコンパイルしない
- パッチに記録された変更だけを作業ツリーへ反映する
- 成功した場合は、通常何も表示されない

変更された4ファイルを確認する。

```bash
git status --short
git diff --check
git diff --stat
```

各コマンドで確認している内容は次のとおり。

| コマンド | 確認内容 |
|---|---|
| `git status --short` | パッチによって、想定した4ファイルが変更状態になったか |
| `git diff --check` | 行末の不要な空白など、差分の書式上の問題がないか |
| `git diff --stat` | どのファイルへ何行追加・削除されたかという差分の概要 |

`git diff --check` も、問題がなければ何も表示されない。

実際に追加されたコードを読む場合は、次のコマンドを使用する。

```bash
git diff
```

`git diff` は、まだコミットしていない変更内容を表示する。
ファイルを書き換えるコマンドではない。

## 6. 改造版FrontISTRをビルドする

標準版と混同しないよう、ビルド先とインストール先を分ける。

- ビルド先: `$HOME/src/FrontISTR/build-dumph`
- インストール先: `$HOME/local/frontistr-dumph`

### 6.1 CMakeでビルド設定を作る

```bash
cd $HOME/src/FrontISTR

cmake -S . -B build-dumph \
  -DCMAKE_BUILD_TYPE=RELEASE \
  -DCMAKE_INSTALL_PREFIX=$HOME/local/frontistr-dumph \
  -DWITH_MPI=OFF \
  -DWITH_OPENMP=ON \
  -DWITH_LAPACK=ON \
  -DWITH_MKL=OFF \
  -DWITH_MUMPS=OFF \
  -DWITH_METIS=OFF \
  -DWITH_NETCDF=OFF \
  -DWITH_REFINER=OFF \
  -DWITH_REVOCAP=OFF \
  -DWITH_TOOLS=OFF \
  -DWITH_DOC=OFF
```

このコマンドは、FrontISTRのソースと利用可能なコンパイラ・ライブラリを調べ、
`build-dumph` フォルダへコンパイル設定を作成する。
この段階ではFrontISTR本体のコンパイルはまだ行わない。

主な指定の意味は次のとおり。

| 指定 | 意味 |
|---|---|
| `cmake` | CMakeを起動する |
| `-S .` | 現在のフォルダをソースフォルダとして使用する |
| `-B build-dumph` | 生成物を `build-dumph` に分離する |
| `CMAKE_BUILD_TYPE=RELEASE` | デバッグ用ではなく、最適化された実行用バイナリを作る |
| `CMAKE_INSTALL_PREFIX=...` | `cmake --install` でコピーする先を指定する |
| `WITH_MPI=OFF` | MPIによる並列領域分割を使用しない |
| `WITH_OPENMP=ON` | 共有メモリ並列のOpenMPを有効にする |
| `WITH_LAPACK=ON` | LAPACKを使用する |
| `WITH_MKL=OFF` | Intel MKLを使用しない |
| `WITH_MUMPS=OFF` | MUMPSソルバーを使用しない |
| その他の `OFF` | 今回不要な追加機能やドキュメントをビルドしない |

設定に成功すると、最後におおむね次のように表示される。

```text
-- Configuring done
-- Generating done
-- Build files have been written to: $HOME/src/FrontISTR/build-dumph
```

### 6.2 コンパイルする

```bash
cmake --build build-dumph -j2
```

- `--build build-dumph`: CMakeが作った設定を使ってコンパイルする
- `-j2`: 2つのコンパイル処理を並行実行する

`-j2` の2は並列数である。CPUコア数ではなく、同時に進めるビルド処理数を
指定している。メモリ使用量を抑えるため、この手順では2としている。

コンパイル途中でエラーが出た場合、インストールへ進まず、最初に表示された
`Error:` 付近を確認する。同じコマンドを再実行すると、通常は未完了部分から
ビルドが再開される。

最後に次の表示が出ればコンパイル成功。

```text
[100%] Built target fistr1
```

### 6.3 インストールする

```bash
cmake --install build-dumph
```

このコマンドは、コンパイル済みの実行ファイルと必要なファイルを、
`CMAKE_INSTALL_PREFIX` で指定した場所へコピーする。

- 新たにソースをコンパイルすることが目的ではない
- この手順では `$HOME/local/frontistr-dumph` へコピーする
- ユーザーのホームフォルダ内なので、通常は `sudo` を付けない
- 通常版の `$HOME/local/frontistr` とは別の場所へ入る

改造版の実行ファイルは次の場所に入る。

```text
$HOME/local/frontistr-dumph/bin/fistr1
```

通常版 `$HOME/local/frontistr/bin/fistr1` は上書きしない。

インストールされた実行ファイルを確認する。

```bash
ls -lh $HOME/local/frontistr-dumph/bin/fistr1
```

- `ls`：ファイルを一覧表示する
- `-l`：権限、所有者、サイズ、更新日時を詳しく表示する
- `-h`：ファイルサイズを読みやすい単位で表示する

## 7. Hを出力する入力設定

`FistrModel.cnt` の `!SOLVER` に `DUMPH=YES` を追加する。

```text
!VERSION
 3
!SOLUTION,TYPE=STATIC
!SOLVER,METHOD=DIRECT,ITERLOG=NO,TIMELOG=YES,DUMPTYPE=MM,DUMPH=YES,DUMPEXIT=YES
 10000, 1
 1.0e-8, 1.0, 0.0
!MATERIAL, NAME=FC300
!ELASTIC, TYPE=ISOTROPIC
 130000.0, 0.27
!EXPANSION_COEFF
 1.2e-5
!END
```

設定の役割は次のとおり。

- `DUMPH=YES`: 温度荷重行列Hを `H_matrix.mtx` に出力する
- `DUMPTYPE=MM`: 全体剛性行列Kと右辺もMatrix Market形式で出力する
- `DUMPEXIT=YES`: K、右辺、Hを出力した後に終了する
- `!EXPANSION_COEFF`: Hの計算に使う線膨張係数を指定する

Hだけが必要な場合でも、材料の `!ELASTIC` と `!EXPANSION_COEFF` は必要になる。Hは形状だけでなく、弾性構成則 $\boldsymbol D$ と線膨張係数 $\alpha$ を含むためである。

## 8. 改造版を実行する

`model/005_H_direct` には `DUMPH=YES` を設定済みの入力一式がある。
この解析フォルダへ移動し、改造版を明示して実行する。

この入力では、比較用の標準RHSを出すため節点2へ単位温度を設定している。
`H_matrix.mtx` はこの温度指定にかかわらず全425列を出力する。

```bash
cd /mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/frontistr/model/005_H_direct
set -o pipefail
$HOME/local/frontistr-dumph/bin/fistr1 2>&1 | tee run_dumph.log
```

各コマンドと記号の意味は次のとおり。

| コマンド・記号 | 意味 |
|---|---|
| `cd .../model/005_H_direct` | 入力ファイルがある解析フォルダへ移動する |
| `/home/.../fistr1` | 通常版ではなく、今回コンパイルした改造版を明示して実行する |
| `2>&1` | エラー出力を標準出力へまとめる |
| `|` | 左側コマンドの出力を右側コマンドへ渡す |
| `tee run_dumph.log` | 画面へ表示しながら、同じ内容をログへ保存する |
| `set -o pipefail` | FrontISTR側が失敗した場合に、パイプライン全体も失敗として扱う |

実行直後に終了コードを確認する場合は、次を実行する。

```bash
echo $?
```

`0` なら直前のパイプラインは正常終了、0以外ならエラー終了である。

実行後、次のファイルを確認する。

```bash
ls -lh H_matrix.mtx dump_matrix_1_0.mm dump_matrix_1_0.rhs
head -n 4 H_matrix.mtx
```

各コマンドの意味は次のとおり。

- `ls -lh ...`：出力ファイルが存在するか、サイズが0でないかを確認する
- `head -n 4 H_matrix.mtx`：Hファイルの先頭4行だけを表示する

`H_matrix.mtx` の先頭では、Matrix Market形式、コメント、行数、列数、
格納成分数を確認できる。

`H_matrix.mtx` の行数・列数は次の意味を持つ。

$$
\boldsymbol H \in \mathbb{R}^{3N_{\mathrm{node}}\times N_{\mathrm{node}}}
$$

- 行: 節点変位自由度。節点1のx、y、z、節点2のx、y、z、…の順
- 列: 節点温度。列 $j$ は節点 $j$ の単位温度による節点熱荷重

## 9. 検証結果

`model/003_Htest` の425節点、1403四面体一次要素モデルで確認した。

- Hの形状: `1275 × 425`
- Matrix Market読込後の非ゼロ数: `13965`
- 節点2へ単位温度を与えた標準RHSとHの第2列を比較
- 最大絶対差: `0.0`
- 相対差: `0.0`

$$
\boldsymbol H[:,2] = \boldsymbol f_{\mathrm{thermal}}(T_2=1)
$$

一様温度ベクトルに対する全外力の各方向合計も約 $10^{-10}$ であり、数値誤差の範囲で自己平衡した。

## 10. 現時点の制限

- 要素タイプ341以外はHへ出力しない
- MPIによる領域分割解析には未対応
- 境界条件適用前の生のHを出力する
- 温度依存材料では一定行列Hとして扱えない
- Matrix Marketには要素ごとの重複成分を含む。SciPyなどの標準的な読込処理では同じ行・列の値が加算される

次の拡張では、341以外の3次元ソリッド対応、重複成分をまとめた出力、MPI対応を個別に検討する。
