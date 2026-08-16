# FrontISTRで温度荷重行列Hを調べて出力する

## 1. この記事の目的

この記事の目的は、FrontISTRで温度荷重行列Hを取り出す方法を明らかにすることである。

具体的には、次の順番で調べた。

- 全体剛性行列Kと同じように、標準の入力キーワードだけでHを出力できるか
- 標準機能で出力できない場合、FrontISTR内部のどこで温度荷重を計算しているか
- ソースコードのどのファイルを変更すれば、Hを直接出力できるか
- 追加したH出力が、FrontISTR標準の温度荷重計算と一致するか

Pythonで $\boldsymbol K^{-1}\boldsymbol H$ を計算する処理は、この記事の対象外とする。

## 2. 先に結論

調査と検証から、次のことが分かった。

- 標準FrontISTRにHを直接出力するキーワードはない
- `!SOLVER,DUMPTYPE=MM` で出力できるのは、係数行列Kと右辺ベクトルRHS
- 温度を与えた解析では、RHSに温度荷重 $\boldsymbol H\boldsymbol T$ が入る
- FrontISTR内部では、全体Hを行列として作っていない
- 標準機能だけでも、節点ごとの単位温度解析を繰り返せばHを1列ずつ取得できる
- H全体を1回で直接出力するには、ソース変更と再コンパイルが必要
- 試作した `DUMPH=YES` によって `H_matrix.mtx` を出力できた
- 出力したHの第2列は、標準FrontISTRの温度荷重RHSと完全一致した

現時点で検証済みなのは、四面体一次要素341、線形材料、単一領域の解析である。

## 3. 温度荷重行列Hとは何か

### 3.1 温度から節点荷重への変換

温度荷重行列Hは、節点温度ベクトル $\boldsymbol T$ を等価節点熱荷重ベクトル $\boldsymbol f_{\mathrm{thermal}}$ へ変換する行列である。

$$
\boldsymbol f_{\mathrm{thermal}}
=
\boldsymbol H\boldsymbol T
$$

各記号の意味は次のとおり。

- $\boldsymbol T$：全節点の温度を並べたベクトル
- $\boldsymbol f_{\mathrm{thermal}}$：温度変化によって発生する等価節点荷重
- $\boldsymbol H$：節点温度を等価節点荷重へ変換する行列

今回のモデルは425節点の3次元ソリッドモデルである。1節点あたりx、y、zの3自由度を持つため、全自由度数は次のようになる。

$$
n_{\mathrm{dof}}
=3\times425
=1275
$$

したがって、Hの大きさは次のとおり。

$$
\boldsymbol H
\in
\mathbb R^{1275\times425}
$$

- Hの行：節点1のx、y、z、節点2のx、y、z、…に対応
- Hの列：節点1の温度、節点2の温度、…に対応

### 3.2 温度から変位への変換

全体剛性行列Kと変位 $\boldsymbol u$ の関係は次式で表される。

$$
\boldsymbol K\boldsymbol u
=
\boldsymbol f_{\mathrm{thermal}}
$$

ここへ $\boldsymbol f_{\mathrm{thermal}}=\boldsymbol H\boldsymbol T$ を代入する。

$$
\boldsymbol K\boldsymbol u
=
\boldsymbol H\boldsymbol T
$$

境界条件を適切に処理した系では、次のように温度から変位を求められる。

$$
\boldsymbol u
=
\boldsymbol K^{-1}\boldsymbol H\boldsymbol T
$$

最終的に求めたい $\boldsymbol K^{-1}\boldsymbol H$ は、節点温度を節点変位へ変換する行列である。

## 4. 物理的に何を計算しているか

### 4.1 温度変化から熱ひずみを求める

等方材料の熱ひずみは、線膨張係数を $\alpha$、現在温度を $T$、初期温度を $T_0$ とすると次式になる。

$$
\boldsymbol\varepsilon_{\mathrm{thermal}}
=
\alpha(T-T_0)
\begin{bmatrix}
1 & 1 & 1 & 0 & 0 & 0
\end{bmatrix}^{\mathsf T}
$$

温度が上昇すると、x、y、z方向に同じ割合の伸びが生じる。せん断方向の熱ひずみは0である。

### 4.2 要素内部の温度を補間する

有限要素では、要素内部の温度を節点温度から補間する。

$$
T(\boldsymbol\xi)
=
\boldsymbol N(\boldsymbol\xi)\boldsymbol T_e
$$

- $\boldsymbol\xi$：要素内の位置
- $\boldsymbol N$：形状関数
- $\boldsymbol T_e$：その要素を構成する節点の温度ベクトル

四面体一次要素341では、1要素に4節点あるため、$\boldsymbol T_e$ は4成分のベクトルになる。

### 4.3 熱ひずみを等価節点荷重へ変換する

要素の等価節点熱荷重は次式で計算する。

$$
\boldsymbol f_{\mathrm{thermal},e}
=
\int_{V_e}
\boldsymbol B^{\mathsf T}
\boldsymbol D
\boldsymbol\varepsilon_{\mathrm{thermal}}
\,\mathrm dV
$$

- $\boldsymbol B$：節点変位から要素ひずみを求める行列
- $\boldsymbol D$：ひずみから応力を求める弾性構成則行列
- $V_e$：要素体積

材料定数が温度に依存せず、初期温度を0とすると、節点温度を行列の外へまとめられる。

$$
\boldsymbol f_{\mathrm{thermal},e}
=
\boldsymbol H_e\boldsymbol T_e
$$

要素温度荷重行列 $\boldsymbol H_e$ は次式になる。

$$
\boldsymbol H_e
=
\int_{V_e}
\boldsymbol B^{\mathsf T}
\boldsymbol D
\alpha
\begin{bmatrix}
1 & 1 & 1 & 0 & 0 & 0
\end{bmatrix}^{\mathsf T}
\boldsymbol N
\,\mathrm dV
$$

FrontISTRは各要素の温度荷重を計算し、それを全体の右辺ベクトルへ足し合わせている。

## 5. どのように調べたか

使用したFrontISTRソースは次の場所にある。

```text
/home/kamakiri/src/FrontISTR
```

ソースのコミットは `7f48eae0`、FrontISTRのバージョンは5.9である。

### 5.1 入力キーワードを読む場所を調べた

最初に、`DUMPTYPE` や行列出力に関する文字列をソース全体から検索した。

確認したファイルは次のとおり。

```text
/home/kamakiri/src/FrontISTR/
└── fistr1/src/common/
    └── fstr_ctrl_common.f90
```

このファイルの `fstr_ctrl_get_SOLVER` が、`!SOLVER` 行の入力を読み取っている。

ソースでは、`DUMPTYPE` が受け付ける値は次のように定義されていた。

```fortran
character(24) :: dlist = '0,1,2,3,NONE,MM,CSR,BSR '
```

この確認から、次のことが分かった。

- `DUMPTYPE=MM`：Matrix Market形式
- `DUMPTYPE=CSR`：CSR形式
- `DUMPTYPE=BSR`：BSR形式
- Hを指定する値は存在しない

### 5.2 行列ダンプが何を出力しているか調べた

次に、実際にファイルを書き出す処理を確認した。

```text
/home/kamakiri/src/FrontISTR/
└── hecmw1/src/solver/matrix/
    └── hecmw_matrix_dump.f90
```

値の一覧だけでは、実際にどのファイルが出るかは分からない。そこで、`DUMPTYPE` を指定したときに動く親ルーチン `hecmw_mat_dump`（同ファイル31行目）を読む。出力の流れはこのルーチンにそのまま書かれている。

```fortran
subroutine hecmw_mat_dump( hecMAT, hecMESH )
  select case( hecmw_mat_get_dump(hecMAT) )     ! DUMPTYPE の値で分岐
    case (NONE) ; return                          ! 何も出さずに戻る
    case (MM)   ; call hecmw_mat_dump_mm(hecMAT)  ! 係数行列K を MM 形式で書く
    case (CSR)  ; call hecmw_mat_dump_csr(hecMAT) ! 係数行列K を CSR 形式で書く
    case (BSR)  ; call hecmw_mat_dump_bsr(hecMAT) ! 係数行列K を BSR 形式で書く
  end select
  call hecmw_mat_dump_rhs(hecMAT)               ! 分岐の外。必ず右辺ベクトルも書く
  if( dump_exit /= 0 ) stop ...                 ! DUMPEXIT=YES ならここで終了
end subroutine
```

処理の流れは次の3ステップである。

1. `DUMPTYPE` の値で分岐し、係数行列（＝K）を選んだ形式で1つだけ書き出す（`select case` なので MM・CSR・BSR のいずれか1つ）。
2. 分岐の外側で `hecmw_mat_dump_rhs` を呼び、右辺ベクトルを書き出す。分岐の外にあるため、`NONE` 以外なら必ず実行される。
3. `DUMPEXIT=YES` なら、ここで `stop` して終了する。

ステップ2で呼ばれる `hecmw_mat_dump_rhs` は、右辺ベクトル `hecMAT%B` を1成分ずつ `.rhs` ファイルへ書き出すだけの処理である。

この流れから、`DUMPTYPE` で出力されるものは次の2種類だと分かる。

- `dump_matrix_*.mm` / `.csr` / `.bsr`：連立方程式の係数行列。静解析では全体剛性行列K（3つは同じKの保存形式違い）
- `dump_matrix_*.rhs`：連立方程式の右辺ベクトル $\boldsymbol f$。温度を与えた解析では、この中身が温度荷重になる

### 5.3 温度荷重がRHSへ入る場所を調べた

温度荷重を組み立てる処理は次のファイルにある。

```text
/home/kamakiri/src/FrontISTR/
└── fistr1/src/analysis/static/
    └── fstr_ass_load.f90
```

処理の流れは次のとおり。

```text
fstr_ass_load
└── process_thermal_loads
    └── calculate_thermal_load
```

要素ごとに計算した温度荷重 `vect` は、次の処理で右辺 `B` へ加算されている。

```fortran
B(iwk(j)) = B(iwk(j)) + vect(j)
```

つまり、温度を設定した解析の `.rhs` には、温度によって発生した等価節点荷重が入る。

### 5.4 3次元要素の温度荷重式を調べた

四面体一次要素341の温度荷重計算は、次のファイルにある。

```text
/home/kamakiri/src/FrontISTR/
└── fistr1/src/lib/
    └── static_LIB_3d.f90
```

この中の `TLOAD_C3` が、3次元ソリッド要素の温度荷重を計算する。

内部では、おおむね次の順番で計算している。

- 形状関数で積分点温度を求める
- 線膨張係数から熱ひずみを求める
- 弾性構成則行列Dを掛けて応力相当量を求める
- $\boldsymbol B^{\mathsf T}$ を掛けて節点荷重へ変換する
- ガウス積分で要素温度荷重ベクトルを求める

### 5.5 調査から分かった重要な点

FrontISTRは、解析中に全体Hを作ってから $\boldsymbol H\boldsymbol T$ を計算しているわけではない。

実際には、各要素で温度荷重ベクトルを直接計算し、全体RHSへ加算している。

```text
節点温度
  ↓
各要素の温度荷重ベクトルを計算
  ↓
全体RHSへ加算
```

したがって、既存のダンプ処理へHを渡すだけでは出力できない。標準FrontISTRのメモリ上に、出力対象となる全体Hが存在しないためである。

## 6. 標準FrontISTRだけでHの1列を取り出す

### 6.1 単位温度を与える理由

Hを列ベクトルで表す。

$$
\boldsymbol H
=
\begin{bmatrix}
\boldsymbol h_1 &
\boldsymbol h_2 &
\cdots &
\boldsymbol h_{n_{\mathrm{node}}}
\end{bmatrix}
$$

節点 $j$ だけが1、他の節点が0の温度ベクトルを $\boldsymbol e_j$ とする。

$$
\boldsymbol e_j
=
\begin{bmatrix}
0 & \cdots & 0 & 1 & 0 & \cdots & 0
\end{bmatrix}^{\mathsf T}
$$

この単位温度ベクトルをHへ掛けると、Hの第 $j$ 列だけが残る。

$$
\boldsymbol H\boldsymbol e_j
=
\boldsymbol h_j
=
\boldsymbol H[:,j]
$$

したがって、節点 $j$ だけに単位温度を与えたときのRHSは、Hの第 $j$ 列になる。

### 6.2 入力ファイルの設定

節点2に単位温度を与える例を示す。

```text
!VERSION
 3
!SOLUTION,TYPE=STATIC
!TEMPERATURE
 2, 1.0
!SOLVER,METHOD=DIRECT,ITERLOG=NO,TIMELOG=NO,DUMPTYPE=MM,DUMPEXIT=YES
 10000, 1
 1.0e-8, 1.0, 0.0
!MATERIAL, NAME=FC300
!ELASTIC, TYPE=ISOTROPIC
 130000.0, 0.27
!DENSITY
 7.4e-9
!EXPANSION_COEFF
 1.2e-5
!END
```

各設定の意味は次のとおり。

| 設定 | 役割 |
|---|---|
| `!TEMPERATURE 2,1.0` | 節点2だけに単位温度を与える |
| `!EXPANSION_COEFF` | 温度から熱ひずみを求める線膨張係数 |
| `DUMPTYPE=MM` | KとRHSをMatrix Market形式で出力する |
| `DUMPEXIT=YES` | 行列とRHSの出力後、方程式を解かずに終了する |
| `!CLOAD`なし | 温度荷重以外をRHSへ混ぜない |
| `!BOUNDARY`なし | 境界条件適用前の生のH列を得る |

実行フォルダは次のとおり。

```text
/mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/model/003_Htest
```

実行コマンドは次のとおり。

```bash
cd /mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/model/003_Htest
/home/kamakiri/local/frontistr/bin/fistr1
```

出力される `dump_matrix_1_0.rhs` は長さ1275のベクトルであり、Hの第2列に相当する。

## 7. H全体を直接出力するために変更した場所

ここまでの6章の方法（1節点に単位温度を与えてRHSを取り出す）でも、H全体は得られる。ただしその場合は、6章の解析を全425節点ぶん、425回くり返す必要がある。この繰り返しはスクリプト `model/004_H/build_H.py` で自動化してある。

この「425回実行する」やり方は動くが手間がかかる。そこで、同じHを**1回の実行**で丸ごと出力する別ルートとして、独自キーワード `DUMPH=YES` を試作した。つまり425回の実行は必須ではなく、それを避けるための改造版を用意した、という位置づけである。以降はこの改造版について説明する。

検証済みパッチは次の場所に保存している。

```text
/mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/
└── patch/
    └── frontistr_dumph_341.patch
```

### 7.1 変更したFrontISTRファイル

```text
/home/kamakiri/src/FrontISTR/
└── fistr1/src/
    ├── common/
    │   ├── fstr_ctrl_common.f90
    │   └── fstr_setup.f90
    ├── lib/
    │   └── m_fstr.F90
    └── analysis/static/
        └── fstr_ass_load.f90
```

各ファイルの変更内容は次のとおり。

| ファイル | 変更内容 |
|---|---|
| `fstr_ctrl_common.f90` | `!SOLVER` で `DUMPH=YES/NO` を読めるようにした |
| `fstr_setup.f90` | 読み取ったDUMPH設定を解析処理へ渡した |
| `m_fstr.F90` | DUMPHの既定値をOFFにした |
| `fstr_ass_load.f90` | 要素341のHを計算し、`H_matrix.mtx` へ出力する処理を追加した |

`static_LIB_3d.f90` の `TLOAD_C3` 自体は変更していない。改造版でもFrontISTR標準の温度荷重計算を再利用している。

### 7.2 改造版がHを求める方法

四面体一次要素には4つの節点がある。要素内の各節点へ順番に単位温度を与え、`TLOAD_C3` を4回呼ぶ。

$$
\boldsymbol H_e\boldsymbol e_1=\boldsymbol H_e[:,1]
$$

$$
\boldsymbol H_e\boldsymbol e_2=\boldsymbol H_e[:,2]
$$

$$
\boldsymbol H_e\boldsymbol e_3=\boldsymbol H_e[:,3]
$$

$$
\boldsymbol H_e\boldsymbol e_4=\boldsymbol H_e[:,4]
$$

この4列を並べると要素Hになる。全要素の寄与を全体節点番号へ対応付けると、全体Hになる。

### 7.3 追加した入力設定

改造版では、`FistrModel.cnt` に次のように記述する。

```text
!SOLVER,METHOD=DIRECT,DUMPTYPE=MM,DUMPH=YES,DUMPEXIT=YES
```

- `DUMPH=YES`：`H_matrix.mtx` を出力する
- `DUMPTYPE=MM`：KとRHSもMatrix Market形式で出力する
- `DUMPEXIT=YES`：出力後に終了する

実行用入力は次のフォルダに用意している。

```text
/mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/model/005_H_direct
```

パッチ適用、ビルド、インストールの全コマンドは、次の記事にまとめている。

```text
docs/05_手順_FrontISTR_DUMPH追加とビルド.md
```

### 7.4 実際にFrontISTRを計算したフォルダ

最初の改造版ビルドと検証は、通常版FrontISTRを変更しないよう、
次の一時フォルダで行った。

```text
/tmp/frontistr-hsrc.1Rzr0X/       改造版ソースとビルド結果
/tmp/fistr-h-test.LVUxwe/         最初の節点2単位温度テスト
```

一時フォルダだけでは後からEasyISTRなどで確認しにくいため、同じ計算を
次のプロジェクト内フォルダで再実行し、入力と出力を保存した。

```text
/mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/model/005_H_direct
```

2026-08-11 01:01（JST）に、上記フォルダで次のコマンドを実行した。

```bash
cd /mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/model/005_H_direct
/tmp/frontistr-hsrc.1Rzr0X/build-h/fistr1/fistr1 > run_dumph.log 2>&1
```

実行は終了コード0で完了した。保存した主なファイルは次のとおり。

| ファイル | 内容 |
|---|---|
| `FistrModel.msh` | 計算に使用したメッシュ |
| `FistrModel.cnt` | 温度、材料、線膨張係数、`DUMPH=YES` の設定 |
| `hecmw_ctrl.dat` | FrontISTRが読むファイルの対応設定 |
| `H_matrix.mtx` | 改造版が直接出力したH |
| `dump_matrix_1_0.mm` | 全体剛性行列K |
| `dump_matrix_1_0.rhs` | 節点2の単位温度によるRHS |
| `run_dumph.log` | 実行ログ |

`FSTR.msg` には、Hの出力に成功したことを示す次のメッセージが残っている。

```text
DUMPH: wrote H_matrix.mtx, shape=1275 425
```

### 7.5 EasyISTRとParaViewで確認できるもの

EasyISTRで設定を確認するときは、次のフォルダを使用する。

```text
/mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/model/005_H_direct
```

EasyISTRでは `FistrModel.msh` から、メッシュ、要素タイプ341、節点グループ、
要素グループ、材料を確認する。解析条件は `FistrModel.cnt` に記録されている。

確認する主な設定は次のとおり。

- `!TEMPERATURE 2,1.0`
- `!ELASTIC`
- `!EXPANSION_COEFF`
- `!SOLVER,...,DUMPH=YES`

`DUMPH` は今回追加した独自キーワードなので、未改造のEasyISTRには
専用の設定画面がない。EasyISTRでモデルを確認し、`DUMPH=YES` は
`FistrModel.cnt` をテキストとして確認する。

ParaViewで形状を確認する場合は、次のファイルを開く。

```text
model/005_H_direct/vtkMeshData/elementGrp_body.vtu
```

このVTUは `005_H_direct/FistrModel.msh` と同一のメッシュから作成したもので、
元のメッシュファイルが一致することを確認している。

`H_matrix.mtx` はMatrix Market形式の行列なので、ParaViewで直接表示する
変位・応力結果ではない。この計算は `DUMPEXIT=YES` で行列出力後に
終了しているため、変位や応力のVTUは出力していない。

フォルダ内のファイルと確認方法は、`model/005_H_direct/README.md` にも
まとめている。

## 8. 何と何を比較したか

### 8.1 比較の目的

改造版がファイルを出力できただけでは、Hの値が正しいとは判断できない。

そこで、改造版が直接出力したHと、標準FrontISTRが従来から計算している温度荷重RHSを比較した。

標準FrontISTRの温度荷重処理を正解側として使用し、改造版のHが同じ結果を再現するか確認した。

### 8.2 比較対象1：改造版が直接出力したHの第2列

- 入力フォルダ：`model/005_H_direct`
- 入力キーワード：`DUMPH=YES`
- 出力ファイル：`H_matrix.mtx`
- Hの大きさ：$1275\times425$
- 比較した部分：第2列 $\boldsymbol H[:,2]$

Hの第2列は、節点2に単位温度を与えたときに全1275自由度へ発生する温度荷重を表す。

### 8.3 比較対象2：標準FrontISTRの温度荷重RHS

- 入力フォルダ：`model/003_Htest`
- 入力キーワード：`!TEMPERATURE 2,1.0`
- 出力ファイル：`dump_matrix_1_0.rhs`
- ベクトルの長さ：1275

このRHSは、節点2だけに単位温度を与えたときに、標準FrontISTRが計算した全自由度の温度荷重である。

### 8.4 比較式

比較した2つは、数式では次の関係になる。

$$
\underbrace{\boldsymbol H[:,2]}_{
\substack{\text{改造版が直接出力した}\\\text{Hの第2列}}
}
\stackrel{?}{=}
\underbrace{\boldsymbol f_{\mathrm{rhs}}(T_2=1)}_{
\substack{\text{標準FrontISTRが計算した}\\\text{温度荷重RHS}}
}
$$

比較したのは1つの値ではなく、長さ1275の2本のベクトルである。

### 8.5 比較結果

結果は次のとおり。

- 最大絶対差：`0.0`
- 相対差：`0.0`

相対差は次式で計算した。

$$
\mathrm{relative\ error}
=
\frac{
\left\|
\boldsymbol H[:,2]
-
\boldsymbol f_{\mathrm{rhs}}(T_2=1)
\right\|_2
}{
\left\|
\boldsymbol f_{\mathrm{rhs}}(T_2=1)
\right\|_2
}
$$

今回の結果は次のとおり。

$$
\mathrm{relative\ error}=0
$$

改造版が出力したHの第2列は、標準FrontISTRの温度荷重RHSと数値的に完全一致した。

## 9. 「うまくいった」の範囲

今回確認できたことは次のとおり。

- `DUMPH=YES` を追加したソースがコンパイルできた
- 改造版FrontISTRから `H_matrix.mtx` を出力できた
- Hの行数と列数が期待した $1275\times425$ になった
- Hの第2列と、標準FrontISTRの節点2単位温度RHSが完全一致した
- 一様温度時の合力が数値誤差の範囲で0になった

一様温度ベクトルを $\boldsymbol 1$ とすると、温度荷重は次式になる。

$$
\boldsymbol f_{\mathrm{uniform}}
=
\boldsymbol H\boldsymbol 1
$$

拘束のない物体が一様に自由膨張する場合、各方向の合力は0になる。

$$
\sum_i f_{x,i}\approx0,
\qquad
\sum_i f_{y,i}\approx0,
\qquad
\sum_i f_{z,i}\approx0
$$

今回の計算でも、各方向の合力は約 $10^{-10}$ 以下だった。

## 10. 確認済みのことと、まだ確認していないこと

Hの全425列を、2つの独立なルートで作って突き合わせた。

- 改造版（`DUMPH=YES`）が1回で出力したH（`model/005_H_direct/H_matrix.mtx`）
- 標準機能を425回くり返して組み立てたH（`model/004_H/build_H.py` → `H_fistr.npz`）

両者は全体で一致した（最大絶対差 `2.2e-10`、相対誤差 `1.5e-12`）。したがって、Hの検証は「第2列のみ」から「全425列」まで完了している。

現時点で未確認の項目は次のとおり。

- $\boldsymbol K^{-1}\boldsymbol H\boldsymbol T$ から求めた変位と、通常のFrontISTR熱応力解析で求めた変位の比較
- 四面体一次要素341以外の要素
- MPIによる領域分割解析
- 温度依存材料

したがって、現時点の「うまくいった」は、**改造版のコンパイル、Hファイルの出力、Hの全425列が標準ルートと一致すること、一様加熱の合力がゼロになることまで確認した**という意味である。

## 11. 注意点

### 初期温度と基準温度

単位温度でHの列を取り出すときは、初期温度を0として扱う。

初期温度や基準温度による定数項がある場合、温度荷重は次の形になる可能性がある。

$$
\boldsymbol f_{\mathrm{thermal}}
=
\boldsymbol H\boldsymbol T
+
\boldsymbol c
$$

この場合、単位温度解析のRHSへ $\boldsymbol c$ が混ざるため、そのままHの列として使用できない。

### 境界条件

今回出力したHは、境界条件適用前の生のHである。

境界条件のない生Kは、剛体並進と剛体回転を含むため特異行列になる。したがって、生Kの逆行列をそのまま計算することはできない。

固定自由度を除いたKとHを使用する。

$$
\boldsymbol K_{ff}\boldsymbol u_f
=
\boldsymbol H_f\boldsymbol T
$$

$$
\boldsymbol u_f
=
\boldsymbol K_{ff}^{-1}\boldsymbol H_f\boldsymbol T
$$

### 温度依存材料

ヤング率、ポアソン比、線膨張係数が温度で変化する場合、Hは一定行列にならない。

この記事の方法は、材料定数が温度に依存しない線形解析を前提としている。

## 12. 関連ファイル

```text
/mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/
├── docs/
│   ├── 00_目次.md
│   ├── 03_温度荷重行列H_FrontISTR標準機能調査.md
│   ├── 04_手順_温度荷重行列H_FrontISTR.md
│   ├── 05_手順_FrontISTR_DUMPH追加とビルド.md
│   ├── 07_WORK_LOG.md
│   └── 08_HANDOFF.md
├── model/
│   ├── 003_Htest/                  標準FrontISTRの単位温度RHS
│   ├── 004_H/                      標準機能でHを列抽出する実験
│   └── 005_H_direct/               DUMPH=YESの実行用入力
└── patch/
    └── frontistr_dumph_341.patch   検証済みソース差分
```
