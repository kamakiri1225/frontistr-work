# `frontistr_dumph_341.patch` — what it does

## Summary

This patch adds a new `!SOLVER` keyword, `DUMPH`, to FrontISTR. When
`DUMPH=YES` is set, a single `fistr1` run exports the **thermal load
transformation matrix** $H$ to `H_matrix.mtx` (MatrixMarket coordinate
format), for first-order tetrahedral elements (element type `341`, C3D4).

$H$ is the matrix such that, for any nodal temperature field $T$, the
equivalent thermal nodal force vector is

$$f_{\text{thermal}} = H\,T$$

$T \in \mathbb{R}^{n_{\text{node}}}$ (one value per node), and
$f_{\text{thermal}} \in \mathbb{R}^{3\,n_{\text{node}}}$ (3 DOF per node), so
$H$ has shape $(3\,n_{\text{node}}) \times n_{\text{node}}$.

Without this patch, the only way to obtain $H$ with an unmodified FrontISTR
is to run the solver once per node with a unit temperature at that node and
collect the resulting load vector (`DUMPTYPE=MM, DUMPEXIT=YES`) — i.e.
$n_{\text{node}}$ full runs (see `post/build_H_tji.py`). This patch collapses
that into a **single run**.

## Where the new code hooks in

| File | Change |
|---|---|
| `fistr1/src/analysis/static/fstr_ass_load.f90` | Adds `export_thermal_matrix_341` and calls it once from the existing load-assembly routine, right after `process_thermal_loads`. |
| `fistr1/src/common/fstr_ctrl_common.f90` | Parses the new `DUMPH` keyword on the `!SOLVER` control line (`NO`/`YES`, like the existing `DUMPEXIT`). |
| `fistr1/src/common/fstr_setup.f90` | Wires the parsed `DUMPH` value into `svIarray(36)`, FrontISTR's internal solver-option array. |
| `fistr1/src/lib/m_fstr.F90` | Initializes `svIarray(36)` to `0` (off) by default. |

The `thermal_matrix_exported` boolean guard ensures the export runs exactly
once, even though the surrounding subroutine may be invoked once per load
step/substep.

## The math behind `export_thermal_matrix_341`

For a single C3D4 element $e$ with local nodes $1,\dots,4$, the standard
thermal load vector (already computed by FrontISTR's existing `TLOAD_C3`
routine for ordinary thermal-stress analysis) is

$$f_e = \int_{V_e} B^T D\, \varepsilon_{\text{th}}\, dV, \qquad \varepsilon_{\text{th}} = \alpha\, \Delta T(x)\, [1,1,1,0,0,0]^T$$

where $B$ is the strain-displacement matrix, $D$ the elastic matrix, $\alpha$
the coefficient of thermal expansion, and $\Delta T(x) = \sum_{k=1}^4 N_k(x)\,T_k$
is the temperature interpolated from the 4 nodal values $T_e=(T_1,T_2,T_3,T_4)$
via the element's shape functions $N_k$.

$f_e$ is **linear** in $T_e$, so an elemental $12\times4$ matrix $H_e$ exists with

$$f_e = H_e\, T_e$$

The patch never derives $H_e$ symbolically — it gets each of its 4 columns by
calling the existing `TLOAD_C3` with a unit temperature at one local node at
a time:

$$T_e = e_k \ (k=1,\dots,4) \quad\Longrightarrow\quad \texttt{TLOAD\_C3}(\dots,\,T_e,\,\dots) = f_e = H_e\,e_k = H_e[:,k]$$

This is exactly the 4-node analogue of the "unit-temperature-per-node" trick
used by `post/build_H_tji.py` at the *global* level — the patch just does it
*inside a single element loop*, reusing the geometry/material context FrontISTR
already has in memory for that element, instead of re-running the whole solver.

## Assembly by duplicate coordinates

Global assembly of finite-element matrices is normally a sum over elements:

$$H = \sum_{e} P_e^T\, H_e\, Q_e$$

($P_e$ scatters local DOF rows to global DOF rows, $Q_e$ scatters local node
columns to global node columns.) The patch does not build this sum in memory.
Instead, for every element and every local node $k$, it writes 12 triplets
`(global_row, global_col, value)` directly to `H_matrix.mtx`:

```fortran
write(iunit,"(I0,' ',I0,' ',e20.12e3)") &
  ndof*(nodLocal(j)-1)+i, nodLocal(k), vect(ndof*(j-1)+i)
```

Nodes shared between elements produce **repeated `(row, col)` pairs** across
different elements. This is intentional (the patch's own comment says so):
MatrixMarket coordinate readers — `scipy.io.mmread`, for example — sum
duplicate entries when building the sparse matrix, which is precisely the
summation in the assembly formula above. No explicit accumulation buffer is
needed in the Fortran code.

## Practical notes

- Single-domain only: the subroutine calls `hecmw_abort` if
  `hecmw_comm_get_size() /= 1`, i.e. `DUMPH` does not support MPI domain
  decomposition.
- Cost: one call to `TLOAD_C3` per local node per `341`-type element, i.e.
  $O(4\,n_{\text{elem,341}})$ — proportional to mesh size, in a single pass,
  versus $O(n_{\text{node}})$ full solver re-runs without the patch.
- Combined with `!BOUNDARY` + `DUMPTYPE=MM` + `DUMPEXIT=YES`, a single run
  also dumps the boundary-condition-applied stiffness matrix $K$
  (`dump_matrix_1_0.mm`) at the same time, using FrontISTR's existing
  (unmodified) `DUMPTYPE=MM` mechanism — see `docs/11_...md` section 1.

## 日本語まとめ

このパッチは、`!SOLVER`に`DUMPH=YES`という新しいキーワードを追加し、
四面体一次要素（341, C3D4）について、温度荷重変換行列
$H$（$f_{\text{thermal}}=HT$の$H$）を**1回の実行**で`H_matrix.mtx`に出力する。

やっていることは、各要素の4つの局所節点それぞれに単位温度（他は0）を与えて、
FrontISTRに既にある`TLOAD_C3`（通常の熱応力解析で使われる関数）を呼び出し、
その結果（要素の熱荷重ベクトル）を$H_e$の1列として書き出す、という操作を
全341要素×4節点ぶん繰り返すだけ。全体行列への組み立ては、節点を共有する
要素同士で同じ(行,列)の組が複数回出力されるように書き出すことで実現しており、
MatrixMarket形式の読み込み側（`scipy.io.mmread`など）が同じ(行,列)の値を
自動的に合計してくれることを利用している（Fortran側で足し合わせる処理を
書く必要がない）。
