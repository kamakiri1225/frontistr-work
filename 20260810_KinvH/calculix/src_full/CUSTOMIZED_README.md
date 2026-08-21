# calculix/src_full — カスタマイズ済み CalculiX ソース一式（そのままビルド可）

パッチ適用や別バージョン取得が要らないよう、**DUMPKH 改造を当てた CalculiX のソース一式**を
そのまま置いてある（他環境でビルドが通らない場合はこちらを使う）。

- **バージョン**：CalculiX **ccx 2.21** に DUMPKH 改造（`calculix/patch/ccx_2.21_dumpkh.patch` 相当、
  `linstatic.c`）と、今の gcc/gfortran・システム ARPACK 向けの `Makefile` 変更を適用済み。
- **含めていないもの**：ビルド生成物（`*.o`・`*.a`・実行ファイル `ccx_2.21`）。
- **SPOOLES は同梱していない**（未改造の外部ライブラリ・約 16MB のため）。ビルド前に
  `calculix/docs/01` の第1章のとおり SPOOLES を用意する（`$HOME/src/calculix_build/SPOOLES.2.2/`
  に `spooles.a` を作る）。ARPACK/LAPACK/BLAS はシステムのものを使う。

## ビルド

```bash
# 1) SPOOLES を用意（calculix/docs/01 §1.2）:  $HOME/src/calculix_build/SPOOLES.2.2/spooles.a
#    このソースは Makefile 内で ../../../SPOOLES.2.2 と ../../../ARPACK を参照するので、
#    次のレイアウトになるように置く：
#      $HOME/src/calculix_build/
#        ├── SPOOLES.2.2/spooles.a
#        └── CalculiX/ccx_2.21/src/   ← ここに src_full/ccx_2.21/src の中身を置く
cp -r calculix/src_full/ccx_2.21 $HOME/src/calculix_build/CalculiX/

# 2) ビルド（Makefile は改造版フラグ入り）
cd $HOME/src/calculix_build/CalculiX/ccx_2.21/src
make
# -> ccx_2.21   （DUMPKH 入りの改造版）
```

実行・使い方は `../docs/01`（`CCX_DUMPKH=1` ＋ `sensitivity_points.dat`）。
