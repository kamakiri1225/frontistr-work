# frontistr/src_full — カスタマイズ済み FrontISTR ソース一式（そのままビルド可）

パッチ適用や別バージョン取得が要らないよう、**DUMPW 改造を当てた FrontISTR のソース一式**を
そのまま置いてある（他環境でビルドが通らない場合はこちらを使う）。

- **バージョン**：FrontISTR **5.9**（`VERSION` = `Version 5.9 (2026/03/20)`、master `7f48eae0`）に
  DUMPW 改造（`frontistr/patch/frontistr_dumpw_tet.patch` 相当）を適用済み。
- 改造したファイルは `fistr1/src/...` の5つ（詳細は `../patch/modified_src/README.md`）。
- **含めていないもの**：`tutorial/`・`tests/`（例題データ、ビルドに不要で重い）、`doc/`、
  ビルド生成物（`build*`・`*.o`・`*.mod`・`*.a`）、`.git`。これらは上流 FrontISTR 5.9 に同梱。

## ビルド（このフォルダで）

```bash
cd frontistr/src_full
cmake -S . -B build -DCMAKE_BUILD_TYPE=RELEASE \
  -DWITH_MPI=OFF -DWITH_OPENMP=ON -DWITH_LAPACK=ON \
  -DWITH_MKL=OFF -DWITH_MUMPS=OFF -DWITH_METIS=OFF \
  -DWITH_NETCDF=OFF -DWITH_REFINER=OFF -DWITH_REVOCAP=OFF \
  -DWITH_TOOLS=OFF -DWITH_DOC=OFF
cmake --build build -j4
# -> build/fistr1/fistr1   （DUMPW 入りの改造版 fistr1）
```

実行・使い方は `../docs/13`・`../docs/14` を参照（`!SOLVER,...,DUMPW=YES` ＋ `sensitivity_points.dat`）。
