# FrontISTR 例題集

[FrontISTR](https://www.frontistr.com/)を使った解析例題を集めるプロジェクトです。
構造解析・熱解析・熱構造解析・振動解析・接触解析など、解析種別ごとに実例（モデル・解析条件・
解説記事）をためていき、FrontISTRで解析設定をするときに参照しやすくすることを目的としています。

## 解析種別ごとの例題

| 解析種別 | フォルダ | 内容 |
| --- | --- | --- |
| 熱構造解析 | [`20260707_biMetal`](20260707_biMetal) | バイメタルの熱応力解析 |
| 熱解析 → 熱構造解析 | [`20260707_biMetal_heatFilm`](20260707_biMetal_heatFilm) | 熱伝導（フィルム係数）から熱膨張応力までの連成解析 |
| 振動解析 | [`20260712_plateEigeResponse`](20260712_plateEigeResponse) | 平板の固有値解析（梁理論との比較）・周波数応答解析 |
| 構造解析（ソース改造） | [`20260810_KinvH`](20260810_KinvH) | FrontISTRから剛性行列K・温度荷重行列Hを取り出しK⁻¹Hを求める。FrontISTRのコンパイル入門記事も含む |
| 接触解析 | （準備中） | |

各フォルダの`docs/`にモデルの解説記事（Markdown、一部WordPress投稿用HTML）を置いています。

## フォルダ構成の目安

```
<例題フォルダ>/
├── FistrModel.msh   # メッシュ・材料定義
├── FistrModel.cnt   # 解析条件（境界条件・荷重・ソルバー設定）
├── hecmw_ctrl.dat   # ファイル入出力の対応付け
└── docs/            # 解説記事・図
    └── img/
```

計算結果ファイル（`*.res.*`, `*.vtu`, 行列ダンプなど）はリポジトリサイズを抑えるため
`.gitignore`で除外しています。手元で`fistr1`を実行すれば再生成できます。

## 環境構築

WSL2でのFrontISTRビルド手順は[`docs/install_wsl.md`](docs/install_wsl.md)を参照してください。
