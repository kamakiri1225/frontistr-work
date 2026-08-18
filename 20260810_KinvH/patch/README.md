# `frontistr_dumph_341.patch` の解説

## 概要

このパッチは、FrontISTRの`!SOLVER`カードに新しいキーワード`DUMPH`を追加する。
`DUMPH=YES`を指定すると、四面体一次要素（要素タイプ`341`, C3D4）について、
**温度荷重変換行列** $H$ を、1回の`fistr1`実行だけで`H_matrix.mtx`
（MatrixMarket coordinate形式）に出力できるようになる。

$H$ は、任意の節点温度場 $T$ に対して、等価な節点熱荷重ベクトルを求める行列である。

$$f_{\text{thermal}} = H\,T$$

$T \in \mathbb{R}^{n_{\text{node}}}$ （節点ごとに1個の温度値）、
$f_{\text{thermal}} \in \mathbb{R}^{3\,n_{\text{node}}}$ （節点ごとに3自由度の力）なので、
$H$ の形は $(3\,n_{\text{node}}) \times n_{\text{node}}$ になる。

このパッチが無い場合、 $H$ を得るには「1節点だけに単位温度を与えて`fistr1`を実行し、
出てきた荷重ベクトルを集める」という操作を**節点数と同じ回数**繰り返す必要がある
（`post/build_H_tji.py`参照）。このパッチは、それを**1回の実行**にまとめる。

## どこにコードが追加されているか

| ファイル | 変更内容 |
|---|---|
| `fistr1/src/analysis/static/fstr_ass_load.f90` | `export_thermal_matrix_341`を新規追加し、既存の荷重組み立てルーチンの中（`process_thermal_loads`の直後）から1回だけ呼び出す。 |
| `fistr1/src/common/fstr_ctrl_common.f90` | `!SOLVER`カードの新しいキーワード`DUMPH`（`NO`/`YES`、既存の`DUMPEXIT`と同じ書式）を読み取る処理を追加。 |
| `fistr1/src/common/fstr_setup.f90` | 読み取った`DUMPH`の値を、FrontISTR内部のソルバーオプション配列`svIarray(36)`に格納する配線を追加。 |
| `fistr1/src/lib/m_fstr.F90` | `svIarray(36)`の既定値を`0`（オフ）に初期化する。 |

`thermal_matrix_exported`という論理型フラグで、荷重組み立てルーチンが荷重ステップ・
サブステップごとに複数回呼ばれても、出力は1回だけに制限している。

## `export_thermal_matrix_341`の中身（数式で）

C3D4要素 $e$ （局所節点1〜4）の熱荷重ベクトルは、通常の熱応力解析でFrontISTRが
既に使っている`TLOAD_C3`というルーチンで計算されている。

$$f_e = \int_{V_e} B^T D\, \varepsilon_{\text{th}}\, dV, \qquad \varepsilon_{\text{th}} = \alpha\, \Delta T(x)\, [1,1,1,0,0,0]^T$$

$B$ はひずみ-変位マトリクス、 $D$ は弾性マトリクス、 $\alpha$ は線膨張係数、
$\Delta T(x) = \sum_{k=1}^4 N_k(x)\,T_k$ は4つの節点温度 $T_e=(T_1,T_2,T_3,T_4)$ から
形状関数 $N_k$ で内挿した温度分布である。

$f_e$ は $T_e$ について**線形**なので、 $12\times4$ の要素行列 $H_e$ が存在して

$$f_e = H_e\, T_e$$

と書ける。パッチは $H_e$ を数式的に導出するのではなく、局所節点1つずつに単位温度を
与えて`TLOAD_C3`を呼び出すことで、 $H_e$ の列を1本ずつ求めている。

$$T_e = e_k \ (k=1,\dots,4) \quad\Longrightarrow\quad \texttt{TLOAD\_C3}(\dots,\,T_e,\,\dots) = f_e = H_e\,e_k = H_e[:,k]$$

これは`post/build_H_tji.py`が全体（グローバル）レベルでやっている
「節点ごとに単位温度を与えて集める」というやり方の、**要素レベル版**に相当する。
すでにメモリ上にある要素の座標・材料情報をそのまま使い回せるので、
ソルバーを丸ごと再実行する必要がない。

## 重複した(行,列)への書き込みで組み立てる

有限要素の全体行列の組み立ては、本来は要素ごとの総和である。

$$H = \sum_{e} P_e^T\, H_e\, Q_e$$

（ $P_e$ は局所自由度を全体自由度に、 $Q_e$ は局所節点を全体節点にスキャッタする行列。）
パッチはこの総和をメモリ上で計算せず、要素ごと・局所節点ごとに12個の
`(全体行, 全体列, 値)`の組を、そのまま`H_matrix.mtx`に書き出している。

```fortran
write(iunit,"(I0,' ',I0,' ',e20.12e3)") &
  ndof*(nodLocal(j)-1)+i, nodLocal(k), vect(ndof*(j-1)+i)
```

節点を共有する要素同士では、同じ`(行, 列)`の組が複数回出力される。これは
意図的なもので（パッチ自身のコメントにもそう書かれている）、`scipy.io.mmread`のような
MatrixMarket形式の読み込み側が、同じ`(行, 列)`の値を自動的に合計してくれることを
利用している。Fortran側で足し合わせ処理を書く必要がない。

## 実務上の注意点

- **単一領域のみ対応**: `hecmw_comm_get_size() /= 1`（MPI領域分割あり）の場合は
  `hecmw_abort`で止まる。`DUMPH`はMPI並列実行に対応していない。
- **コスト**: `341`要素1個・局所節点1個につき`TLOAD_C3`を1回呼ぶだけなので、
  計算量は $O(4\,n_{\text{elem,341}})$ （メッシュサイズに比例）。パッチ無しで
  節点数ぶん`fistr1`を再実行する方式（ $O(n_{\text{node}})$ 回のフルソルブ）より
  はるかに軽い。
- **Kも同時に出せる**: `!BOUNDARY`＋`DUMPTYPE=MM`＋`DUMPEXIT=YES`と組み合わせると、
  境界条件適用後の剛性行列 $K$ （`dump_matrix_1_0.mm`）も**同じ1回の実行**で
  同時に出力できる（FrontISTR標準の`DUMPTYPE=MM`機構をそのまま利用、パッチ不要の部分）。
  詳しくは`docs/11_...md`のセクション1を参照。
