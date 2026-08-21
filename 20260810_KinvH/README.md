# 20260810_KinvH — 熱感度（K・H・W・VTK）を FrontISTR と CalculiX で

節点温度に対する変位感度 `W = K^-1 H`（および剛性 `K`、温度荷重 `H`、その VTK）を、
**2 つのソルバを改造して**出力・比較したプロジェクト。フォルダは**ソルバごとに分離**してある。

```
20260810_KinvH/
├── frontistr/        ← FrontISTR 版（DUMPH / DUMPW 改造）
│   ├── model/            解析モデル（001〜012。011=一次, 012=二次 四面体）
│   ├── patch/            改造パッチ（*.patch）＋ modified_src/（改造したソース実ファイル）＋ README
│   ├── src_full/         カスタマイズ済み FrontISTR 5.9 ソース一式（パッチ不要でそのままビルド可）
│   ├── post/             Python 後処理（アジョイント W、VTK、341→342 変換 など）
│   ├── docs/             手順・解説（00_目次 〜 14、img/）
│   └── sample/           元の感度解析サンプル
└── calculix/         ← CalculiX 版（ccx を改造して K・H・W・VTK を出力）
    ├── model/011_Tji_ccx/   CalculiX 入力デックと出力
    ├── patch/               ccx_2.21_dumpkh.patch ＋ modified_src/（改造した linstatic.c 等）
    ├── src_full/            カスタマイズ済み ccx 2.21 ソース一式（そのままビルド可、SPOOLESは別途）
    ├── post/                （参考）Python 後処理
    └── docs/01_...          導入・改造・実行・結果の手順書
```

## どちらも同じことをする

| | FrontISTR | CalculiX |
|---|---|---|
| 改造の入口 | `!SOLVER,DUMPW=YES`（`frontistr/patch/frontistr_dumpw_tet.patch`） | 環境変数 `CCX_DUMPKH=1`（`calculix/patch/ccx_2.21_dumpkh.patch`） |
| 出力 | K・H・W・VTK（すべてソルバ内） | K・H・W・VTK（すべてソルバ内） |
| 要素 | 一次 341 ＋ 二次 342 | 一次 C3D4（＝341）のみ |
| 測定点 | `sensitivity_points.dat`（`19 103`） | 同左 |

感度 `Wdiff` は両ソルバで**相関 0.9995・相対差 約 3%**で一致（残りは独立 2 コードの
一次四面体の実装差）。詳しくは各 `docs/` を参照。

- FrontISTR：`frontistr/docs/13`（DUMPW 基礎）、`frontistr/docs/14`（一次/二次・K/H/W/VTK・数式とプログラム）
- CalculiX：`calculix/docs/01`（導入・改造・数式とプログラム・結果）
