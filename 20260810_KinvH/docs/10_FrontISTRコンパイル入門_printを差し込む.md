# FrontISTRを自分でコンパイルしてみる（printを差し込む入門）

こんにちは（@t_kun_kamakiri）。

FrontISTRはソースコードが公開されているので、自分で書き換えてコンパイルできます。とはいえ、いきなり難しい改造をすると「コンパイルのやり方が悪いのか、書き換えが悪いのか」が分からなくなりがちです。

そこでこの記事では、いちばん簡単な練習として **「print文を1つ差し込んで、コンパイルが成功したことを画面に出す」** をやってみます。あわせて、変数を定義して $a+b=c$（$a=1,\ b=2$）を計算し、答えの3を表示させます。これができれば、FrontISTRの「書き換え → コンパイル → 実行」の一周を体験できます。

---

## 本記事の概要

- FrontISTRのソースに1か所だけ print文を差し込む
- 変数を定義して $a+b=c$ を計算し、結果を表示する
- コンパイル（ビルド）して実行し、`コンパイル成功` と `1 + 2 = 3` が出るのを確認する

*FrontISTR 5.9 / WSL2環境に構築*

この記事は、まず **手順パート**（フォルダ構成 → 編集 → コンパイル → モデル用意 → 実行）で「書き換え → コンパイル → 実行」を一周し、そのあとの **詳しい解説** で、各ステップが何をしているのかを1つずつ掘り下げる構成です。まず動かしたいだけなら、手順パートだけで完了します。

---

## 使った環境

今回コンパイルした環境は次のとおりです。

| 項目 | 内容 |
|---|---|
| OS | Ubuntu 24.04（WSL2） |
| コンパイラ | GNU Fortran 13.3.0 |
| ビルドツール | CMake 3.28.3 |
| FrontISTR | バージョン5.9（Gitコミット `7f48eae0`） |

FrontISTRのソースは、次の場所にあるものとします。

```text
/home/kamakiri/src/FrontISTR
```

FrontISTRはFortran言語で書かれているため、Fortranに慣れている人であればソースコードをかなり読み解きやすいと思います。

---

## フォルダ構成と編集するファイル

FrontISTRの実行ファイル `fistr1` を起動すると、最初にC言語の `main()` がコマンドラインやMPIの初期処理を行い、そのあとFortranの `fstr_main()` を呼び出します。解析処理はこの `fstr_main()` から進むので、ここに print 文を入れると計算の実行時に表示されます。

書き換えるファイルは、次の1つだけです。

```text
fistr1/src/main/fistr_main.f90
```

このパスは、FrontISTRソースの `/home/kamakiri/src/FrontISTR` を起点とした相対パスです。フォルダ構成の中での位置は、次のようになっています。

```text
/home/kamakiri/src/FrontISTR/     ← FrontISTRソースの起点
├── CMakeLists.txt                  ビルドルール
├── fistr1/                         FrontISTR本体（構造・熱解析など）
│   └── src/
│       ├── analysis/               解析アルゴリズム
│       ├── common/                 共通処理
│       ├── lib/                    要素剛性など計算ライブラリ
│       └── main/                   起動まわり
│           ├── main.c              C言語の入口 main()
│           └── fistr_main.f90      ★ 今回書き換えるファイル（fstr_main）
├── hecmw1/                         土台ライブラリ HEC-MW（メッシュ・並列・入出力）
└── build_test/                     ビルド作業用フォルダ
```

`fistr1/` がFrontISTR本体、`hecmw1/` がそれを支える土台ライブラリ（HEC-MW）です。今回さわるのは `fistr1/src/main/` の中の1ファイルだけです。なお `build_test/` は最初から存在するわけではなく、あとのコンパイルで作られる作業用フォルダです（ここでは位置関係を示すために一緒に描いています）。

ここで、よく似た名前が2つ出てきます。混同しやすいので先に整理しておきます。

| 名前 | 何か | 綴り |
|---|---|---|
| `fistr_main.f90` | 書き換える**ファイル**名 | `i` が入る（f**i**str） |
| `fstr_main` | そのファイルの中にある**サブルーチン**名 | `i` が入らない（fstr） |

以降でも、末尾が `.f90` ならファイル、そうでなければサブルーチンを指します。

---

## 編集する

ファイル `fistr1/src/main/fistr_main.f90` を開き、その中の `fstr_main` サブルーチン（37行目あたりから始まります）の先頭に、2か所を書き足します。差し込む場所は「初期化が終わったあたり（`hecmw_comm_get_size` の直後）」です。

**(1) 変数の宣言**（`real(kind=kreal) :: T1, T2, T3` の下）に1行:

```fortran
    integer(kind=kint) :: a, b, c
```

**(2) 初期化の直後**（`nprocs = hecmw_comm_get_size()` の下）に print のまとまり:

```fortran
    if( myrank == 0 ) then
      a = 1
      b = 2
      c = a + b
      print *, '==========================================='
      print *, ' Hello from customized FrontISTR!'
      print *, ' コンパイル成功 (compile succeeded)'
      print *, ' a + b = c  ->', a, '+', b, '=', c
      print *, '==========================================='
    endif
```

`integer` の宣言や `if( myrank == 0 )`、`print` の文法は、後半の「編集したコードの詳しい解説」で1つずつ説明します。ここではこのまま書き足せば大丈夫です。

---

## コンパイルする

**はじめての場合**（設定してからビルド）:

```bash
cd /home/kamakiri/src/FrontISTR

cmake -S . -B build_test \
  -DCMAKE_BUILD_TYPE=RELEASE \
  -DWITH_MPI=OFF -DWITH_MKL=OFF -DWITH_MUMPS=OFF \
  -DWITH_METIS=OFF -DWITH_ML=OFF -DWITH_REFINER=OFF \
  -DWITH_LAPACK=ON \
  -DCMAKE_INSTALL_PREFIX=$HOME/local/frontistr

cmake --build build_test -j2
```

最初の `cmake -S . -B build_test ...` は、ビルドの準備です。どのコンパイラを使うか、どの機能を使う／使わないか（`-DWITH_MPI=OFF` など）を決めて、`build_test` というフォルダに設定を書き出します。ここではまだコンパイルは始まりません。

次の `cmake --build build_test -j2` で、実際にコンパイルして実行ファイル `fistr1` を作ります。初回は全部をコンパイルするので、少し時間がかかります。

一度ビルドしたあとは、ソースを直すたびに次だけでOKです。変更した部分だけコンパイルし直すので、すぐ終わります。

```bash
cmake --build build_test --target fistr1 -j2
```

各オプションの意味や、`build_test` の中身は、後半の「コンパイルの詳しい解説」でくわしく扱います。

---

## 動作確認用モデルを用意する

実行して確認するには、入力となる解析モデルが必要です。この記事では、確認用に**四面体1個だけの小さなモデル**を用意しています。静解析で、節点が4つしかないので一瞬で終わり、print の確認にちょうどよいです。

`model/007_compile_test/` に、次の3ファイルを置いています。

- `FistrModel.msh` … メッシュ（節点・要素）と材料
- `FistrModel.cnt` … 解析条件（静解析・境界条件・荷重・材料）
- `hecmw_ctrl.dat` … FrontISTRにどのファイルを使うかを教える指定

各ファイルの中身は、後半の「解析設定（モデル）の詳しい解説」で説明します。ここではこのモデルをそのまま使えばOKです。

---

## 実行して確認する

確認用モデルのフォルダへ移動して、作った `fistr1` を実行します。

```bash
cd /mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/model/007_compile_test
/home/kamakiri/src/FrontISTR/build_test/fistr1/fistr1
```

1行目は、FrontISTRの入力ファイルがある解析フォルダへ移動しています。FrontISTRは通常、実行時の現在地から `hecmw_ctrl.dat` を探し、そこに書かれたメッシュや制御ファイルを読み込みます。そのため、実行ファイルがある `build_test` ではなく、解析入力のある `007_compile_test` へ移動します。

2行目で、その場所から、別フォルダにあるコンパイル済みFrontISTRを起動しています。このパスは `~`（ホームフォルダ）を使って `~/src/FrontISTR/build_test/fistr1/fistr1` と書いても同じです。手入力では `~` が短くて便利ですが、この記事ではどのフォルダを使ったか分かるよう絶対パスで書いています。

実行すると、計算のログの中に、書き足した表示が出てきます。

```text
 ===========================================
  Hello from customized FrontISTR!
  コンパイル成功 (compile succeeded)
  a + b = c  ->           1 +           2 =           3
 ===========================================
 Step control not defined! Using default step=1
 fstr_setup: OK
### Relative residual = 0.00000E+00
 FrontISTR Completed !!
```

`コンパイル成功` と `a + b = c -> 1 + 2 = 3` が表示され、最後まで計算が進んで `FrontISTR Completed !!` で終わっています。これで、

1. ソースを書き換える
2. コンパイルする
3. 実行して結果を確認する

という一周ができました。自分の書き換えが、ちゃんと実行ファイルに反映されていることも確認できます。

ここまでが手順パートです。動かすだけならこれで完了です。ここから先は、各ステップが何をしているのかを詳しく見ていきます。

---

## ここからは詳しい解説

ここから先は、手順パートで行った内容を、1つずつ掘り下げて説明します。動かすだけなら読まなくても大丈夫ですが、「なぜそう書くのか」を理解したいときに読んでください。

---

## 編集したコードの詳しい解説

「編集する」で書き足したのは、`fstr_main` サブルーチンの先頭部分でした。まず、そのファイル全体がどんな形をしているかを眺めてから、書き足した各行の意味を見ていきます。

### ファイル全体の骨格

`fistr_main.f90` 全体の骨格だけを示すと、次のようになっています（`...（省略）...` の部分は今回は読まなくて大丈夫です）。

```fortran
module m_fstr_main

  use hecmw          ! 土台ライブラリ HEC-MW の定義（kreal, hecmw_init など）
  use m_fstr         ! FrontISTR共通の変数（myrank, nprocs など）
  ...（ほかにも解析・入出力用のモジュールを use）...

  ! --- モジュール全体で共有するデータ（メッシュ・行列・解析条件など） ---
  type(hecmwST_local_mesh), save :: hecMESH    ! メッシュ（節点・要素）
  type(hecmwST_matrix), save     :: hecMAT     ! 全体剛性行列など
  type(fstr_solid), save         :: fstrSOLID  ! 構造解析のデータ
  ...（ほかにも熱・固有値・動解析用のデータが並ぶ）...

contains

  ! ★ 実行の入口。C の main() から呼ばれるのはここ（今回さわるのもここ）
  subroutine fstr_main() bind(C,NAME='fstr_main')
    ...（INITIALIZE → ANALYSIS → FINALIZE と進む。詳細は後述の「発展：ステージごとにprintを置いて流れを追う」）...
  end subroutine fstr_main

  subroutine fstr_init             ! 初期化と .cnt ファイルの読み込み
    ...（省略）...
  end subroutine fstr_init

  subroutine fstr_init_file        ! ログ・メッセージ用ファイルを開く
    ...（省略）...
  end subroutine fstr_init_file

  subroutine fstr_init_condition   ! fstr_setup を呼んで解析条件を読む
    ...（省略）...
  end subroutine fstr_init_condition

  subroutine fstr_static_analysis  ! 静解析（今回の解析はここに入る）
    ...（省略）...
  end subroutine fstr_static_analysis

  subroutine fstr_eigen_analysis   ! 固有値解析
    ...（省略）...
  end subroutine fstr_eigen_analysis

  subroutine fstr_heat_analysis    ! 熱伝導解析
    ...（省略）...
  end subroutine fstr_heat_analysis

  subroutine fstr_dynamic_analysis ! 動解析
    ...（省略）...
  end subroutine fstr_dynamic_analysis

  subroutine fstr_static_eigen_analysis  ! 静解析 → 固有値解析
    ...（省略）...
  end subroutine fstr_static_eigen_analysis

  subroutine fstr_finalize         ! 後始末（ファイルを閉じる）
    ...（省略）...
  end subroutine fstr_finalize

end module m_fstr_main
```

この骨格の読み方は次のとおりです。

- **`module m_fstr_main` 〜 `end module m_fstr_main`** … ファイル全体が1つの「モジュール」で包まれています。モジュールは、関連する変数と処理をひとまとめにする箱のようなものです。
- **`use ...`（冒頭）** … 他のモジュールで定義された変数や処理を借りてくる宣言です。これで `kreal` や `hecmw_init`、`myrank` などをこのファイルの中で使えます。
- **`type(...) :: hecMESH` など** … メッシュや行列といった、複数のサブルーチンで共有する大きなデータをここでまとめて宣言しています。`save` は、処理が終わっても中身を保持する指定です。
- **`contains`** … これ以降が、このモジュールが持つサブルーチンの定義です。`fstr_main` はこの `contains` の直後、先頭にあります。
- **`fstr_main` 以外のサブルーチン** … `fstr_init`（初期化）や `fstr_static_analysis`（静解析）などです。`fstr_main` がこれらを順に呼び出して解析を進めます。役割は後述の「発展：ステージごとにprintを置いて流れを追う」で改めて扱うので、ここでは「こういう部品が並んでいる」とだけ分かれば十分です。

今回さわるのは、この中の `fstr_main` の先頭部分だけです。

### サブルーチンの宣言部を読む

「編集する」の (1) で書き足したのは、次の宣言部でした。

```fortran
  subroutine fstr_main() bind(C,NAME='fstr_main')
    implicit none
    real(kind=kreal) :: T1, T2, T3
    integer(kind=kint) :: a, b, c   ! ← 追加：コンパイル学習用の変数
```

この数行は、「`fstr_main` という処理の定義」と「その中で使う変数の宣言」に分かれます。順に見ていきます。

#### `subroutine fstr_main()`

`subroutine` は、Fortranでひとまとまりの処理を定義するキーワードです。`fstr_main` がその処理名です。

```fortran
subroutine fstr_main()
```

丸括弧 `()` の中には、呼び出し元から受け取る引数を書きます。この `fstr_main()` は空なので、引数はありません。

ちなみにFortranには主に `subroutine` と `function` の2種類の処理があります。

| 種類 | 特徴 | 呼び出し方の例 |
|---|---|---|
| `subroutine` | 戻り値を式として返さない処理 | `call hecmw_init` |
| `function` | 値を1つ返し、式の中で使える処理 | `myrank = hecmw_comm_get_rank()` |

いちおうこの記事はFrontISTRの理解とFortranやCの理解も兼ねて、文法部分はできるだけ解説しようと思います。

#### `bind(C, NAME='fstr_main')`

サブルーチンの後ろに `bind(C,NAME='fstr_main')` と書く文法は、私自身あまり馴染みがありませんでした。

```fortran
  subroutine fstr_main() bind(C,NAME='fstr_main')
```

ざっくり言うと、これは **このFortranサブルーチンを、C言語のプログラムから呼び出せるようにする** ための指定です。そのしくみの1つとして、コンパイルのときに `fstr_main` という名前を（コンパイラに勝手に変えられないよう）そのまま付けてコンパイルさせています。この「名前をそのままにする」意味は、あとの「名前をそろえる」で詳しく説明します。

まず前提として、**FrontISTRは1つのプログラムですが、中身は2つの言語を組み合わせて作られています**。

- **プログラムの入口（最初に動く部分）… C言語で書かれ、ファイルは `main.c`。** `fistr1` を実行したとき、いちばん最初に動くのがここです。`-v`（バージョン表示）などのオプションを読んだり、並列計算（MPI）を立ち上げたりといった、解析を始める前の準備を担当します。
- **解析の中身（計算の本体）… Fortranで書かれ、ファイルは `fistr_main.f90`。** メッシュを読み込み、剛性行列を組み立てて方程式を解く、FEM計算の中心部分です。数値計算はFortranが得意なので、この部分はFortranで書かれています。

つまり、**準備はC言語、計算はFortran**、という役割分担です。そのため実行すると、まずC側の `main()`（`main.c`）が動き、準備が終わるとFortran側の `fstr_main`（`fistr_main.f90`）を呼び出します。

ところが、**C言語とFortranは別々の言語なので、そのままでは互いの処理を呼び合えません**。この「言語の壁」を越えて、C側からFortran側の `fstr_main` を呼べるようにするのが `bind(C,NAME='fstr_main')` です。指定は次の2つの部分に分かれます。

| 部分 | ざっくり何をするか |
|---|---|
| `bind(C)` | 呼び出しの「作法」をC言語に合わせる |
| `NAME='fstr_main'` | 呼び出すときの「名前」をC言語に合わせて `fstr_main` に固定する |

「作法」と「名前」の2つが合って初めて、C側からFortran側を呼べます。まず「呼び出す」とは何かを確認し、続けてこの2つをかみ砕いて説明します。

##### 「呼び出す」の意味

プログラムでいう「呼び出す（呼ぶ）」とは、**あるコードが、別のまとまった処理に「この仕事をやっておいて」と依頼し、実行してもらってから、元の場所に戻ってくる**ことです。人に用事を頼むのに近いイメージです。

さきほどの役割分担でいうと、C言語の準備係が、自分の準備を終えたあとに「あとは解析をお願い」とFortranの計算係へ処理を渡します。この「処理を渡す」動作が、`main.c` に書かれた `fstr_main();` という1行、つまり `fstr_main` の**呼び出し**です。だからFrontISTRを実行すると、C（準備）→ Fortran（計算）の順に処理が進みます。

「名前で呼ぶ」というのは、この依頼のときに **相手を名前で指名する** ということです。`main.c` の `fstr_main();` は、「`fstr_main` という名前の処理をやって」という指名になっています。だから、指名する名前（C側）と、指名される側の名前（Fortran側）が一致していないと、相手が見つからず呼び出せません。ここで問題になるのが、次に説明する「作法」と「名前」です。

##### C言語と同じ呼び出し規約（作法をそろえる）

**呼び出し規約**とは、ある処理を呼ぶときの「引数をどこに置いて渡すか」「戻り値をどう受け取るか」といった、細かい手順の取り決めのことです。

`bind(C)` を付けると、このFortranサブルーチンを **「C言語と同じ作法」で呼べる形** にしてくれます。これで、C側は普通のC関数を呼ぶのと同じ感覚で `fstr_main` を呼べるようになります。

##### コンパイル後に名前が変わる問題（名前をそろえる）

もう1つが名前です。まず前提として、**私たちがソースに書いた `fstr_main` という名前は、コンパイル後のプログラムにそのままの文字で残るとは限りません**。

コンパイルすると、ソースコードは機械語（コンピュータが直接実行できる形）に変換されます。このとき各サブルーチンには、プログラムの中でその処理を見つけ出すための「ラベル」が付きます。ラベルとは、いわば**処理に貼られる名札**です。さきほどの「名前で呼ぶ」で相手を探すときは、ソースに書いた名前ではなく、この名札（ラベル）を目印にして探します。

やっかいなことに、Fortranコンパイラは、この名札を作るときに、書いた名前そのままではなく、**モジュール名などをくっつけた別の名前に作り変えることがあります**。これを**名前マングリング**と呼びます。

たとえばGNU Fortranで、`bind(C)` を付けずに `module m_fstr_main` の中の `fstr_main` をコンパイルすると、ラベルは次のような名前になります。

```text
__m_fstr_main_MOD_fstr_main      ← 「モジュール名 m_fstr_main の中の fstr_main」という意味の名前
```

つまり、**`fstr_main` という名前（名札）ではコンパイルされず、別の名前になってしまう**、ということです。処理の中身はどちらでも同じですが、外から見える名札だけが `fstr_main` から `__m_fstr_main_MOD_fstr_main` に変わります。

これは、別のモジュールに同じ名前のサブルーチンがあっても取り違えないよう、コンパイラが自動で付けている工夫です。

一方、C側（`main.c`）は、あくまで `fstr_main` という名前のまま呼ぼうとします。

```c
extern void fstr_main();   /* Fortran側を "fstr_main" という名前で呼ぶ、という宣言 */
...
fstr_main();               /* コマンドライン処理などの後に、ここで呼び出す */
```

すると、C側が探す名前（`fstr_main`）と、Fortran側の実際のラベル（`__m_fstr_main_MOD_fstr_main`）が食い違います。この状態でプログラムを1つに結合（リンク）しようとすると、「`fstr_main` という名前が見つからない」というエラーになってしまいます。

そこで `NAME='fstr_main'` を付けると、Fortran側もラベルを作り変えず、**書いたとおりの `fstr_main` のまま**にします。

```text
bind(C) なし : __m_fstr_main_MOD_fstr_main   ← C側の fstr_main と食い違う（つながらない）
bind(C) あり : fstr_main                      ← C側の fstr_main と一致（つながる）
```

これで、C側が呼ぶ `fstr_main` と、Fortran側のラベル `fstr_main` がぴったり一致し、無事に呼び出せるようになります。FrontISTRの起動部分（C側）は次のファイルにあります。

```text
fistr1/src/main/main.c
```

##### 練習で書き換えるときの注意

今回の練習では、`bind(C,NAME='fstr_main')` の部分には手を触れません。ここを変えるとC側から呼べなくなり、FrontISTRが起動しなくなります。この行は「C（`main.c`）とFortran（`fistr_main.f90`）をつなぐ約束事」なので、そのまま残しておきます。

FrontISTRが起動する流れを簡略化すると、次のようになります。

```text
Linuxが実行ファイル fistr1 を起動
        ↓
main.c の main()
        ↓
コマンドラインやMPIの初期処理
        ↓
Fortranの fstr_main()
        ↓
メッシュ読み込み、剛性行列組立て、解析
```

#### `implicit none`

Fortranには、宣言していない変数の型を、変数名の先頭文字から自動的に決める古い規則があります。`implicit none` はその自動判定を無効にし、使用する変数をすべて明示的に宣言させます。

```fortran
implicit none
```

例えば `myrank` を間違えて `myrnak` と書いたとき、`implicit none` があれば未宣言変数としてコンパイルエラーになります。変数名の書き間違いを早く発見するための重要な指定です。

#### `real(kind=kreal) :: T1, T2, T3`

`real` は、小数を扱う実数型です。`kind=kreal` は、FrontISTRで共通使用する実数の種類を指定しています。

```fortran
real(kind=kreal) :: T1, T2, T3
```

この宣言は次のように分解できます。

| 部分 | 意味 |
|---|---|
| `real` | 実数型 |
| `(kind=kreal)` | FrontISTR共通の実数精度を使う |
| `::` | 型や属性と、変数名の区切り |
| `T1, T2, T3` | 宣言する3つの実数変数 |

FrontISTR 5.9では、`kreal` は次のファイルに定義されています。

```text
hecmw1/src/common/hecmw_util_f.F90
```

```fortran
integer(kind=4), parameter :: kreal = 8
```

`fistr_main.f90` のモジュール先頭にある `use hecmw` がHEC-MWの定義を取り込んでいるため、`fstr_main` の中で `kreal`、`kint`、`hecmw_init` などを使えます。`use` は、他のFortranモジュールで公開されている定義を現在のモジュールから利用するためのキーワードです。

今回使用したGNU Fortranでは、`real(kind=8)` は通常、8バイトの倍精度実数に対応します。FrontISTRでは解析に使う実数の精度を `kreal` という名前で共通化しています。

`T1`、`T2`、`T3` には、FrontISTRの初期化前後や解析後の時刻が入ります。最後に差を取り、前処理時間や解析時間を表示するための変数です。

#### `integer(kind=kint) :: a, b, c`

`integer` は整数型です。`kind=kint` は、FrontISTRで共通使用する整数の種類を指定しています。

```fortran
integer(kind=kint) :: a, b, c
```

`kint` も `hecmw_util_f.F90` で次のように定義されています。

```fortran
integer(kind=4), parameter :: kint = 4
```

今回使用したGNU Fortranでは、`integer(kind=4)` は通常、4バイトの整数に対応します。`a`、`b`、`c` は今回の練習で追加する3つの整数変数です。

`kind` の数値が常にバイト数を表すことはFortran規格全体で保証されていません。ここでは、今回のGNU Fortran環境とFrontISTRの定義に基づいて説明しています。

### print文の記述

「編集する」の (2) で書き足したのは、次のまとまりでした。

```fortran
    call hecmw_init
    myrank = hecmw_comm_get_rank()
    nprocs = hecmw_comm_get_size()

    ! ===== コンパイル学習用に差し込んだ print 文 =====
    if( myrank == 0 ) then
      a = 1
      b = 2
      c = a + b
      print *, '==========================================='
      print *, ' Hello from customized FrontISTR!'
      print *, ' コンパイル成功 (compile succeeded)'
      print *, ' a + b = c  ->', a, '+', b, '=', c
      print *, '==========================================='
    endif
```

#### HEC-MWの初期化とプロセス番号の取得

print文の直前にある3行は、FrontISTRの基盤ライブラリであるHEC-MWを初期化し、並列実行の情報を取得する処理です。

```fortran
call hecmw_init
myrank = hecmw_comm_get_rank()
nprocs = hecmw_comm_get_size()
```

##### `call hecmw_init`

`call` はFortranのサブルーチンを呼び出すキーワードです。ここでは `hecmw_init` という初期化処理を呼んでいます。

`hecmw_init` の定義は次にあります。

```text
hecmw1/src/common/hecmw_util_f.F90
```

この処理の主な役割は次のとおりです。

- 既定の制御ファイル名を `hecmw_ctrl.dat` にする
- HEC-MWの通信情報を初期化する
- MPI有効時は、MPIからプロセス数と自分のランクを取得する
- `hecmw_ctrl.dat` を読むための制御情報を初期化する

MPI有効版では、C側の `main.c` がそれより前に `MPI_Init` を実行しています。Fortran側の `hecmw_init` は、そのMPI実行環境からプロセス数とランクを取得し、HEC-MW内部で使えるようにします。

今回は、CMake設定で `-DWITH_MPI=OFF` を指定し、**あえてMPI（並列計算）を使わない構成でビルドしています**。このように並列を使わない直列構成にすると、HEC-MW内部では次の値が設定されます。

```text
プロセス数 = 1
自分のランク = 0
```

##### `myrank = hecmw_comm_get_rank()`

`hecmw_comm_get_rank()` は、現在このコードを実行しているプロセスの番号を返す関数です。戻り値を `myrank` に代入しています。

```fortran
myrank = hecmw_comm_get_rank()
```

ランク番号は0から始まります。例えば4プロセスで実行する場合、各プロセスの `myrank` は次のいずれかになります。

```text
0, 1, 2, 3
```

`myrank` は `m_fstr.F90` でFrontISTR共通の整数変数として宣言されており、`fistr_main.f90` では `use m_fstr` を通じて使っています。

##### `nprocs = hecmw_comm_get_size()`

`hecmw_comm_get_size()` は、並列実行に参加している全プロセス数を返す関数です。戻り値を `nprocs` に代入しています。

```fortran
nprocs = hecmw_comm_get_size()
```

例えば4プロセスで実行している場合、すべてのプロセスで `nprocs=4` になります。`nprocs` も `m_fstr.F90` でFrontISTR共通の整数変数として宣言されています。

今回の `WITH_MPI=OFF` では、結果は常に次のようになります。

```text
myrank = 0
nprocs = 1
```

そのため、続く次の条件は真になり、print文が1回表示されます。

```fortran
if (myrank == 0) then
```

各行の意味は次のとおりです。

- `if( myrank == 0 ) then` … 並列計算のとき全プロセスが同じことを表示すると邪魔なので、代表の1プロセス（rank 0）だけが表示するようにしています。
- `a = 1` / `b = 2` … 変数に値を入れます。
- `c = a + b` … 足し算の結果を `c` に入れます（$1+2=3$）。
- `print *, ...` … 画面（標準出力）に文字や変数の値を表示します。`print *,` は「書式はおまかせで表示する」という意味です。
- `'...'` … シングルクォートで囲んだ部分はそのまま文字列として表示されます。

---

## コンパイルの詳しい解説

「コンパイルする」で使ったビルドコマンドを、もう少し細かく見ていきます。

### CMakeの役割

CMake自体がFrontISTRのFortranソースを直接コンパイルするわけではありません。CMakeはソースの `CMakeLists.txt` を読み、コンパイラやライブラリを調べて、「どのファイルをどの順番でコンパイルするか」というビルド設定を作ります。

作業は次の3段階に分かれます。

```text
1. CMake設定
   FrontISTRのソース
   /home/kamakiri/src/FrontISTR
             ↓ cmake -S . -B build_test

2. コンパイル
   ビルド用フォルダ
   /home/kamakiri/src/FrontISTR/build_test
             ↓ cmake --build build_test

3. インストール
   完成した実行ファイルを利用場所へコピー
   /home/kamakiri/local/frontistr
             ↑ cmake --install build_test
```

この3つは別の処理です。最初の `cmake -S ... -B ...` だけでは、まだFrontISTR本体のコンパイルもインストールも行われません。

### 設定コマンドとコンパイルコマンドの違い

手順で使った2つのコマンドは、役割がはっきり分かれています。

| コマンド | 何をするか | 実行ファイルは |
|---|---|---|
| `cmake -S . -B build_test ...`（設定） | `CMakeLists.txt` を読み、コンパイラやライブラリを調べ、`-D...` の設定を反映して、`build_test` に手順書（`Makefile` など）を作る。**まだコンパイルしない** | まだできない |
| `cmake --build build_test -j2`（コンパイル） | `build_test` の手順書に従い、実際にソースを機械語へ変換し、結合して `fistr1` を作る。`-j2` は2つ並行 | ここでできる |

料理でたとえると、**設定が「レシピと材料の準備」、コンパイルが「実際の調理」**です。

### 全ファイルがコンパイルされるのか、変更分だけか

コンパイル（`cmake --build`）で毎回すべてを作り直すわけではありません。状況によって変わります。

- **初回**（まだ何も作っていない状態）… **FrontISTRの全ソースがコンパイル**されます。ファイル数が多いので、数分〜十数分かかります。
- **2回目以降**（ソースを1か所直しただけ）… **変更したファイルと、その影響を受ける部分だけ**が再コンパイルされ、最後に `fistr1` を結合し直します。変えていないファイルは前回の結果を使い回すので、数十秒で終わります。

たとえば `fistr_main.f90` を1つ直しただけなら、コンパイルし直されるのは基本的に `fistr_main.f90` の分だけで、あとはリンク（結合）をやり直すだけです。

この「どこを直したか、どこに影響するか」の判定は、**設定のときに `build_test/CMakeFiles` へ記録された依存関係**にもとづいて、CMakeが自動で行います。私たちが「このファイルだけ」と指定する必要はありません。

### CMakeの設定コマンド

```bash
cd /home/kamakiri/src/FrontISTR

cmake -S . -B build_test \
  -DCMAKE_BUILD_TYPE=RELEASE \
  -DWITH_MPI=OFF -DWITH_MKL=OFF -DWITH_MUMPS=OFF \
  -DWITH_METIS=OFF -DWITH_ML=OFF -DWITH_REFINER=OFF \
  -DWITH_LAPACK=ON \
  -DCMAKE_INSTALL_PREFIX=$HOME/local/frontistr
```

各指定の意味は次のとおりです。

| 指定 | 意味 |
|---|---|
| `cmake` | CMakeを起動する |
| `-S .` | 現在のフォルダ `.` をソースフォルダとして読む |
| `-B build_test` | `build_test` をビルド用フォルダとして使う |
| `-D変数名=値` | CMakeの設定変数に値を与える |
| `CMAKE_BUILD_TYPE=RELEASE` | デバッグ用ではなく、最適化した実行用バイナリを作る |
| `WITH_MPI=OFF` | MPI領域分割を使わない |
| `WITH_MKL=OFF` | Intel MKLを使わない |
| `WITH_MUMPS=OFF` | MUMPSソルバを使わない |
| `WITH_METIS=OFF` | METISを使わない |
| `WITH_ML=OFF` | MLプリコンディショナを使わない |
| `WITH_REFINER=OFF` | メッシュ細分化機能をビルドしない |
| `WITH_LAPACK=ON` | LAPACKを有効にする |
| `CMAKE_INSTALL_PREFIX=...` | `cmake --install` を実行したときのコピー先を指定する |

`$HOME` はホームフォルダを表す環境変数です。今回の環境では、`$HOME/local/frontistr` は `/home/kamakiri/local/frontistr` と同じ意味です。

### `build_test` フォルダの役割

`build_test` という名前に特別な意味はありません。`build`、`build-release`、`build-test` など、分かりやすい名前を任意に付けられます。今回は作業を区別するため `build_test` としています。

`build_test` がまだ存在しない場合は、CMakeが自動的に作成します。`mkdir build_test` を事前に実行する必要はありません。

設定後のフォルダには、おおむね次のものが入ります。

```text
/home/kamakiri/src/FrontISTR/
├── CMakeLists.txt               FrontISTRのビルドルール
├── fistr1/                      FrontISTRのソースコード
├── hecmw1/                      HEC-MWのソースコード
└── build_test/                 コンパイル作業用
    ├── CMakeCache.txt            CMakeが記憶した設定
    ├── CMakeFiles/               依存関係などの作業ファイル
    ├── Makefile                  コンパイル手順
    └── fistr1/fistr1             コンパイル後の実行ファイル
```

ここに示したのは `build_test` 内の主な項目です。実際には、ライブラリやサブフォルダなど、FrontISTRのビルドに必要な他の生成物も入ります。

| 項目 | 種類 | 何が入っているか | 手で編集するか |
|---|---|---|---|
| `CMakeCache.txt` | テキストファイル | CMakeの設定値と、コンパイラ・ライブラリの検出結果 | 通常は編集しない |
| `CMakeFiles/` | ディレクトリ | CMakeがビルドを管理するための内部情報 | 編集しない |
| `Makefile` | テキストファイル | `make`が読むビルド対象と処理手順 | 編集しない |
| `fistr1/fistr1` | 実行ファイル | FortranやCのソースをコンパイル・結合したFrontISTR本体 | 編集しない |

`fistr1/fistr1` は、同じ名前が2回続いていて紛らわしいですが、次の意味です。

```text
build_test/fistr1/fistr1
           │       └─ 実行ファイル名
           └─ fistr1用のビルド結果を置くディレクトリ
```

これは、GNU FortranやGCCが各ソースをオブジェクトファイルへコンパイルし、リンカが結合して作った、Linuxで実行可能なバイナリファイルです。テキストエディタで開いてもFortranソースのようには読めません。動作を変えるときは `fistr1/src/` 以下のソースを編集し、もう一度コンパイルします。

ソースとビルド中間ファイルを分けておくと、設定をやり直すときに `build_test` だけを作り直せばよく、FrontISTRのソースと混ざりません。また、設定の違うビルドを並べて保持することもできます（例：`build-release/`、`build-debug/`、`build_test/`）。

### コンパイルの実行

設定ができたら、次でビルドします。

```bash
cmake --build build_test -j2
```

- `--build build_test` … さきほど作った設定でコンパイルします。
- `-j2` … 2つのコンパイル処理を並行します。数を大きくすると速くなる場合がありますが、メモリ使用量も増えます。

このコマンドを実行して初めて、コンパイラがFrontISTRのソースを機械語へ変換し、実行ファイル `fistr1` を作ります。成功すると最後に `[100%] Built target fistr1` と表示され、実行ファイルが `build_test/fistr1/fistr1` にできます。

### インストールの意味

`CMAKE_INSTALL_PREFIX` はコンパイル結果を直接作る場所ではありません。次のインストールコマンドを実行したときに、コンパイル済みの実行ファイルと必要なファイルがコピーされる先です。

```bash
cmake --install build_test
```

今回の指定では、完成品は `/home/kamakiri/local/frontistr` の下へ配置されます。したがって2つの場所の役割は次のように異なります。

| 場所 | 役割 |
|---|---|
| `/home/kamakiri/src/FrontISTR/build_test` | CMakeの設定、コンパイル途中のファイル、コンパイル結果を置く作業場所 |
| `/home/kamakiri/local/frontistr` | 完成したFrontISTRを日常の解析で使うためのインストール先 |

### 2回目以降のビルド（変更後の再ビルド）

一度ビルドしてある場合、ソースを書き換えたあとは `fistr1` をビルド対象に指定して再ビルドできます。

```bash
cd /home/kamakiri/src/FrontISTR
cmake --build build_test --target fistr1 -j2
```

- `cmake --build build_test` … `build_test` に作成済みのビルド設定を使います。
- `--target fistr1` … CMakeが定義した `fistr1` というビルド対象を完成させます。ここでの `fistr1` は**フォルダ名ではなく、実行ファイル `fistr1` を作るためのビルド対象名**です。
- `-j2` … 2つのビルド処理を並行します。

CMakeが管理している依存関係により、変更したソースとその影響部分だけが再コンパイルされ、最後に `fistr1` が作り直されます。「`fistr1` フォルダだけをコンパイルする」という意味ではなく、「`fistr1` を完成させるのに必要な範囲だけをビルドする」という意味です。

次の書き方も、今回のMakefile構成ではほぼ同じ処理です。

```bash
cd /home/kamakiri/src/FrontISTR/build_test
make fistr1
```

`make` は `build_test` の中にCMakeが生成した `Makefile` を読みます。ただし、CMakeがMakefile以外のビルド方式を生成する環境でも同じ手順を使えるため、この記事では `cmake --build ... --target fistr1` の書き方を基本とします。

---

## 解析設定（モデル）の詳しい解説

「動作確認用モデルを用意する」で使った四面体1個のモデルの中身を見ておきます。

**メッシュ `FistrModel.msh`**（先頭の `#` 行はコメント。以降のブロックは `!` で始まります）:

```text
!HEADER
 3
!NODE
 1, 0.0, 0.0, 0.0
 2, 10.0, 0.0, 0.0
 3, 0.0, 10.0, 0.0
 4, 0.0, 0.0, 10.0
!ELEMENT, TYPE=341, EGRP=body
 1, 1, 2, 3, 4
!NGROUP, NGRP=fix
 1, 2, 3
!NGROUP, NGRP=force
 4
!MATERIAL, NAME=FC300, ITEM=2
!ITEM=1, SUBITEM=2
 130000.0, 0.27
!ITEM=2, SUBITEM=1
 7.4e-09
!SECTION, TYPE=SOLID, EGRP=body, MATERIAL=FC300
!END
```

おもなブロックの意味は次のとおりです。

| ブロック | 意味 |
|---|---|
| `!NODE` | 節点の座標。ここでは4点で四面体を作る |
| `!ELEMENT, TYPE=341` | 四面体1次要素（341）を1個定義（`1, 1, 2, 3, 4` = 要素1が節点1・2・3・4からなる） |
| `!NGROUP, NGRP=fix` / `force` | 固定する節点グループ（1〜3）／荷重をかける節点グループ（4） |
| `!MATERIAL` / `!SECTION` | 材料の値と、それを要素グループ `body` に割り当てる指定 |

**解析条件 `FistrModel.cnt`**:

```text
!VERSION
 3
!WRITE,RESULT
!SOLUTION,TYPE=STATIC
!BOUNDARY
 fix, 1, 1, 0.0
 fix, 2, 2, 0.0
 fix, 3, 3, 0.0
!CLOAD
 force, 1, 100.0
!SOLVER,METHOD=DIRECT,ITERLOG=NO,TIMELOG=YES
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

| ブロック | 意味 |
|---|---|
| `!SOLUTION,TYPE=STATIC` | 静解析を行う |
| `!BOUNDARY` | `fix` グループ（節点1〜3）を x・y・z 方向に固定（`fix, 1, 1` は自由度1＝x を固定の意味） |
| `!CLOAD` | `force` グループ（節点4）の x方向に 100 N の集中荷重 |
| `!MATERIAL` `!ELASTIC` | ヤング率 130000 MPa、ポアソン比 0.27。`!DENSITY` 密度、`!EXPANSION_COEFF` 線膨張係数 |
| `!SOLVER,METHOD=DIRECT` | 連立方程式を直接法で解く |

単位系は **mm-ton-s** です（両ファイルの先頭にも `#` コメントで書いています）。

| 量 | 単位 |
|---|---|
| 長さ | mm |
| 力 | N |
| 応力・ヤング率 | MPa（= N/mm²） |
| 密度 | ton/mm³ |
| 時間 | s |
| 温度 | ℃（線膨張係数は 1/℃） |

なお、**材料の値を `.cnt` と `.msh` の両方に書いた場合は、`.cnt` の値が優先されます**。FrontISTRはメッシュ側の材料を先に読み込み、そのあと `.cnt` の `!MATERIAL` を同じ材料名（ここでは `FC300`）で照合して上書きするためです。今回はどちらも同じ値（E=130000 MPa など）にそろえています。

---

## 実行ファイルの使い分け（fistr1 とフルパス・インストール）

「実行して確認する」では、わざわざ長いフルパスを打って実行しました。

```bash
/home/kamakiri/src/FrontISTR/build_test/fistr1/fistr1
```

一方、ふだんは `fistr1` とだけ打って動かしている人も多いと思います。この2つは、**別の実行ファイルを指していることがある**ので注意が必要です。

- **フルパスで実行** … 書いたパスの実行ファイルがそのまま動きます。今回は `build_test/fistr1/fistr1`、つまり**書き換えた版**（print を書き足してコンパイルしたもの）です。
- **`fistr1`（パスなし）で実行** … シェルが環境変数 PATH に登録されたフォルダから `fistr1` を探し、最初に見つかったものを動かします。多くの環境では、これは前にインストールしてある**元の版**（書き換える前のもの）です。

いま自分がどちらを実行しようとしているかは、次で確認できます。

```bash
which fistr1     # 「fistr1」と打つとどの実行ファイルが動くか、その場所を表示する
```

たとえば次のように表示されたら、`fistr1`（パスなし）で動くのはインストール済みの版です。

```text
/home/kamakiri/local/frontistr/bin/fistr1
```

これは、CMake設定で指定した `-DCMAKE_INSTALL_PREFIX=$HOME/local/frontistr` の場所です。`build_test` の中の書き換えた版とは別物なので、**`fistr1` とだけ打つと、書き換えた版ではなく元の版が動きます**。どちらが動いているかは、実行時に最初に出る `build:` の `date:` でも見分けられます（書き換えてビルドし直した日付なら書き換えた版、それより古い日付なら元の版）。

### 書き換えた版を `fistr1` で使いたい場合（インストール）

「フルパスは長いので、`fistr1` とだけ打って書き換えた版を動かしたい」という場合は、**インストール**します。

今回のインストールでは、次の対応でファイルが反映されます。

```text
コピー元（ビルドした書き換え版）
/home/kamakiri/src/FrontISTR/build_test/fistr1/fistr1
                          ↓ cmake --install build_test
コピー先（日常的に fistr1 で呼ぶ版）
/home/kamakiri/local/frontistr/bin/fistr1
```

`cmake --install` は `fistr1` だけを手作業でコピーするコマンドではありません。CMakeが生成したインストール手順に従い、実行ファイルと必要な関連ファイルを `CMAKE_INSTALL_PREFIX` の下へ配置します。今回の `CMAKE_INSTALL_PREFIX` は `$HOME/local/frontistr` です。

#### 1. 書き換えたソースを再ビルドする

インストールの前に、最新のソースから `build_test/fistr1/fistr1` を作り直します。

```bash
cd /home/kamakiri/src/FrontISTR
cmake --build build_test --target fistr1 -j2
```

最後に次が表示されれば、書き換えた版のコンパイルは成功です。

```text
[100%] Built target fistr1
```

#### 2. インストール前の2つの版を確認する

まず、パスを省略した `fistr1` がどのファイルを指すかを確認します。

```bash
command -v fistr1
```

今回の環境では、次が表示されます。

```text
/home/kamakiri/local/frontistr/bin/fistr1
```

続けて、ビルドフォルダの書き換え版と、現在インストールされている版のビルド日時を比較します。

```bash
/home/kamakiri/src/FrontISTR/build_test/fistr1/fistr1 -v
fistr1 -v
```

2026年8月13日のインストール前の確認では、次のようにビルド日時が異なっていました。

```text
build_testの書き換え版: 2026-08-13T22:34:23+0900
インストール済みの版: 2026-07-07T23:25:33+0900
```

この時点では、`fistr1` とだけ入力すると、7月7日にビルドしたインストール済みの版が実行されます。8月13日にコンパイルした書き換え版は、まだインストール先に反映されていません。

#### 3. `build_test` の書き換え版をインストールする

```bash
cd /home/kamakiri/src/FrontISTR
cmake --install build_test
```

このコマンドは、`build_test` に作成されたインストール設定を読み、コンパイル済みの `build_test/fistr1/fistr1` を含む必要ファイルを `/home/kamakiri/local/frontistr` の下へ配置します。既に `/home/kamakiri/local/frontistr/bin/fistr1` がある場合は、その実行ファイルが書き換えた版に更新されます。

#### 4. インストール後に反映を確認する

```bash
command -v fistr1
fistr1 -v
```

`command -v fistr1` が引き続き次を示し、`fistr1 -v` の `build:` 内の `date:` が `build_test` 版と同じ日時になっていれば、反映できています。

```text
/home/kamakiri/local/frontistr/bin/fistr1
```

最後に解析フォルダで `fistr1` を実行し、追加したprint文が表示されることを確認します。

```bash
cd /mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/model/003_Htest
fistr1
```

`fistr1 -v` はビルド日時を確認するためのコマンドです。今回 `fstr_main()` の中へ追加したprint文が本当に入っているかは、実際の解析を実行して表示を確認するのが最も確実です。

ただし1つ注意があります。インストールすると `~/local/frontistr/bin/fistr1` が上書きされるので、**このシステムで `fistr1` を使う他の作業も、すべて書き換えた版に切り替わります**（計算結果は変わりませんが、書き足した表示が混ざります）。他の作業に影響させたくない場合は、インストールせず、これまでどおりフルパスで実行するか、別名を付けて使い分けます。たとえば次のようにエイリアスを作れば、`fistr1`（元の版）はそのままで、`fistr1c` で書き換えた版を呼べます。

```bash
alias fistr1c='/home/kamakiri/src/FrontISTR/build_test/fistr1/fistr1'
```

---

## 発展：ステージごとにprintを置いて流れを追う

ここまでは `fstr_main` の入口に1か所だけ print を差し込みました。ここでは一歩進んで、`fstr_main` が**解析全体をどういう順番で進めているのか**を眺めながら、その要所要所に print を置いてみます（追加の編集と再ビルドをする発展的な内容です）。処理の流れが画面で追えるようになります。

### fstr_main の役割（解析の司令塔）

`fstr_main`（`fistr1/src/main/fistr_main.f90` の37行目〜）の中身は、コメントの区切りに沿って大きく3つのステージに分かれています。

```fortran
  subroutine fstr_main() bind(C,NAME='fstr_main')
    ...

    ! =============== INITIALIZE ===================
    call hecmw_init                        ! 土台ライブラリ HEC-MW を初期化
    myrank = hecmw_comm_get_rank()         ! 自分のプロセス番号
    nprocs = hecmw_comm_get_size()         ! 全プロセス数

    T1 = hecmw_Wtime()                     ! 時間計測スタート
    name_ID = 'fstrMSH'
    call hecmw_get_mesh( name_ID , hecMESH )   ! メッシュ（節点・要素）を読む
    call hecmw2fstr_mesh_conv( hecMESH )       ! FrontISTR内部形式へ変換
    call fstr_init                             ! データ初期化＋cntファイル読み込み
    call fstr_rcap_initialize( ... )
    T2 = hecmw_Wtime()

    ! =============== ANALYSIS =====================
    select case( fstrPR%solution_type )        ! 解析の種類で振り分け
      case( kstSTATIC )      ; call fstr_static_analysis     ! 静解析
      case( kstDYNAMIC )     ; call fstr_dynamic_analysis    ! 動解析
      case( kstEIGEN )       ; call fstr_eigen_analysis      ! 固有値
      case( kstHEAT )        ; call fstr_heat_analysis       ! 熱伝導
      case( kstSTATICEIGEN ) ; call fstr_static_eigen_analysis
    end select
    T3 = hecmw_Wtime()

    ! （ここで TOTAL / pre / solve の実行時間を表示）

    ! =============== FINALIZE =====================
    call fstr_rcap_finalize( ... )
    call fstr_finalize()               ! メッセージファイルなどを閉じる
    call hecmw_dist_free(hecMESH)      ! メッシュのメモリ解放
    call hecmw_finalize
    if(...) write(*,*) 'FrontISTR Completed !!'
  end subroutine fstr_main
```

3つのステージの役割は次のとおりです。

| ステージ | コメントの区切り | やっていること |
|---|---|---|
| STAGE 1 | `INITIALIZE` | HEC-MWの初期化、メッシュと解析条件（`.cnt`）の読み込み、データ構造の準備 |
| STAGE 2 | `ANALYSIS` | `solution_type` に応じて解析本体を呼ぶ。静解析なら `K u = f` を組み立てて解く |
| STAGE 3 | `FINALIZE` | 結果ファイルを閉じ、メモリを解放して終了。最後に `FrontISTR Completed !!` |

`T1`（開始）、`T2`（前処理おわり）、`T3`（解析おわり）で時刻を測り、あとで差を取って前処理時間・解析時間を表示しています。

`select case` の `fstrPR%solution_type` は、`.cnt` の `!SOLUTION,TYPE=` で決まる値です。今回の静解析は `kstSTATIC`（値は `1`）なので、`fstr_static_analysis` に入ります。

### 各ステージへの print の追加

流れを目で追えるように、各ステージの入口に1行ずつ print を足します。すでにある「Hello / a+b=c」のブロックはそのままで、次の3行を追加します。

```fortran
    ! （Hello / a+b=c のブロックの直後）
    if( myrank == 0 ) print *, '### STAGE 1: INITIALIZE (前処理・メッシュと条件の読み込み) ###'
```

```fortran
    ! =============== ANALYSIS =====================
    if( myrank == 0 ) print *, '### STAGE 2: ANALYSIS (solution_type =', fstrPR%solution_type, ') ###'

    select case( fstrPR%solution_type )
```

```fortran
    ! =============== FINALIZE =====================
    if( myrank == 0 ) print *, '### STAGE 3: FINALIZE (結果の後始末・ファイルを閉じる) ###'

    call fstr_rcap_finalize( fstrPR, fstrCPL )
```

いずれも `if( myrank == 0 )` を付けています。これは、並列（MPI）実行のときに全プロセスが同じ行を出すと画面が重複するので、**代表の1プロセス（rank 0）だけが表示する**ためです。今回の `WITH_MPI=OFF` では常に `myrank=0` なので、1回ずつ表示されます。

`print *, '...', 変数, '...'` のように、`print` の後ろはカンマ区切りで文字列と変数を混ぜて並べられます。STAGE 2 では `fstrPR%solution_type` の値もそのまま表示しています。

### 再ビルドと流れの確認

書き換えたら、これまでと同じように `fistr1` を作り直します。

```bash
cd /home/kamakiri/src/FrontISTR
cmake --build build_test --target fistr1 -j2
```

解析フォルダで実行すると、計算の進行に合わせて3つのステージが順番に表示されます。

```text
 ===========================================
  Hello from customized FrontISTR!
  コンパイル成功 (compile succeeded)
  a + b = c  ->           1 +           2 =           3
 ===========================================
 ### STAGE 1: INITIALIZE (前処理・メッシュと条件の読み込み) ###
 ### STAGE 2: ANALYSIS (solution_type =           1 ) ###
 ### STAGE 3: FINALIZE (結果の後始末・ファイルを閉じる) ###
 FrontISTR Completed !!
```

`solution_type = 1`（静解析）に入り、INITIALIZE → ANALYSIS → FINALIZE の順に進んで、最後に `FrontISTR Completed !!` で終わっていることが分かります。

このように、**「気になる場所の直前に print を置いて、実行時にそこを通ったか確かめる」** のは、ソースを読むときの基本のやり方です。どの関数がどの順番で呼ばれているのかを確かめながら読むと、大きなプログラムでも迷子になりにくくなります。

---

## 元に戻す手順

練習が終わって元のFrontISTRに戻したいときは、書き足したprint文と変数宣言をソースから削除し、もう一度 `fistr1` をビルドします。

まず変更内容を確認します。

```bash
cd /home/kamakiri/src/FrontISTR
git diff -- fistr1/src/main/fistr_main.f90
```

このファイルに今回の練習以外の変更がないことを確認した上で、書き足した行をエディタで削除します。その後、次で作り直します。

```bash
cd /home/kamakiri/src/FrontISTR
cmake --build build_test --target fistr1 -j2
```

もし練習前の状態にそのまま戻したいだけなら、`git` で1つのファイルを元に戻すのが簡単です。

```bash
cd /home/kamakiri/src/FrontISTR
git checkout fistr1/src/main/fistr_main.f90
cmake --build build_test --target fistr1 -j2
```

---

## まとめ

- FrontISTRは `fistr1/src/main/fistr_main.f90` の `fstr_main` に print文を書き足すだけで、実行時に好きな表示を出せます。
- ビルドはCMakeで行い、初回は `cmake -S . -B build_test ...` で設定してから `cmake --build build_test -j2` でコンパイルします。
- 2回目以降は `cmake --build build_test --target fistr1 -j2` とすると、変更したファイルと依存部分だけが自動判定されて再ビルドされます。
- `fistr1`（パスなし）は PATH上の**元の版**、フルパスの `build_test/fistr1/fistr1` は**書き換えた版**を指します。書き換えた版を `fistr1` で使いたいときは `cmake --install build_test` でインストールします。
- `fstr_main` は INITIALIZE → ANALYSIS → FINALIZE の3ステージで進みます。各ステージの頭に print を置くと、実行時にどこを通っているかを目で追えます。

この「書き換え → コンパイル → 実行」の流れが分かれば、次はもっと意味のある改造（たとえば温度荷重行列Hを出力する `DUMPH=YES` の追加など）にも進めます。実際のHの改造は `05_手順_FrontISTR_DUMPH追加とビルド.md` にまとめています。
