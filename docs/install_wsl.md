# FrontISTR を WSL(Ubuntu) にインストールする手順

このドキュメントは、Windows 上の WSL (Ubuntu 24.04 LTS) に FrontISTR をソースからビルドしてインストールした手順をまとめたものです。
実際にこの環境 (`DESKTOP-KL00V01`) で使われている構成を記載しています。

## 環境情報

- OS: Ubuntu 24.04.3 LTS (noble) on WSL2
- カーネル: `6.6.87.2-microsoft-standard-WSL2`
- FrontISTR バージョン: 5.9 (git hash `7f48eae0b13111aee8d4f1fefef692e9281f0ce6`)
- ビルド日時: 2026-06-06T01:04:56+0900
- ビルド構成: MPI 無効 / OpenMP 有効 / LAPACK 有効 / METIS 無効

## 1. 依存パッケージのインストール

ビルドに必要な最小限のパッケージは以下の通りです（`sudo` 権限が必要）。

```bash
sudo apt update
sudo apt install -y build-essential gfortran cmake git \
    liblapack-dev libblas-dev
```

MPI 並列版や METIS によるメッシュ分割を使う場合は、追加で以下も導入します
（今回の環境ではインストール済みですが、ビルド設定では未使用 = OFF）。

```bash
sudo apt install -y libopenmpi-dev openmpi-bin libmetis-dev libscalapack-openmpi-dev
```

## 2. ソースの取得

```bash
mkdir -p ~/src
cd ~/src
git clone https://github.com/FrontISTR/FrontISTR.git
cd FrontISTR
```

## 3. CMake によるビルド設定

インストール先は `~/local/frontistr` とし、ビルドディレクトリ `build-codex` を作成して構成しました。

```bash
cd ~/src/FrontISTR
cmake -S . -B build-codex \
    -DCMAKE_BUILD_TYPE=RELEASE \
    -DCMAKE_INSTALL_PREFIX=$HOME/local/frontistr \
    -DWITH_MPI=OFF \
    -DWITH_OPENMP=ON \
    -DWITH_LAPACK=ON \
    -DWITH_METIS=OFF \
    -DWITH_ML=OFF \
    -DWITH_MUMPS=OFF
```

## 4. ビルド & インストール

```bash
cmake --build build-codex -j$(nproc)
cmake --install build-codex
```

インストール後、実行ファイルは以下に生成されます。

```
~/local/frontistr/bin/fistr1
```

## 5. PATH の設定（任意）

`fistr1` はデフォルトでは PATH に含まれていないため、フルパスで実行するか、
`~/.bashrc` に以下を追記して PATH を通します。

```bash
export PATH="$HOME/local/frontistr/bin:$PATH"
```

## 6. インストール確認

```bash
$ ~/local/frontistr/bin/fistr1 -v
##################################################################
#                         FrontISTR                              #
##################################################################
---
version:      5.9
git_hash:     7f48eae0b13111aee8d4f1fefef692e9281f0ce6
build:
  date:       2026-06-06T01:04:56+0900
  MPI:        disabled
  OpenMP:     201511
  OpenACC:    disabled
  option:    "--with-lapack "
---
```

## 補足

- Windows 側 (`fistr1` が見つからずエラーになったログ = `FistrModel.log` 参照) では
  FrontISTR は未インストールのため、計算は WSL 側の `fistr1` を使う必要がある。
- Windows のパス `D:\work\...` は WSL からは `/mnt/d/work/...` としてアクセスする。
- MPI 並列やメッシュ分割 (METIS) が必要になった場合は、上記 3. の cmake オプションを
  `-DWITH_MPI=ON -DWITH_METIS=ON` に変更し、`libopenmpi-dev` / `libmetis-dev` を利用して
  再ビルドする。
