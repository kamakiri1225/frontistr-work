# CAE WordPress Blog Style Reference

## Source Templates

Use these local files as the primary style examples when accessible:

```text
/mnt/d/work/002_CAE/openfoam/20260505_datadoka/sample/101_1_frontistr_cht_box_thermal_expansion/docs/02_blog.md
/mnt/d/work/002_CAE/openfoam/20260505_datadoka/sample/101_1_frontistr_cht_box_thermal_expansion/docs/【OpenFOAM×FrontISTR】ヒートマットで温めた金属ブロックの熱膨張を時刻歴で計算する.html
```

The current FrontISTR article is another concrete WordPress block example:

```text
/mnt/d/work/002_CAE/frontistr/work/20260810_KinvH/docs/【徹底解説】FrontISTRのfstr_mainにprintを追加してコンパイルする手順.html
```

Inspect source files for style only. Re-derive facts from the target project and do not carry model values, dates, paths, or conclusions into a different article.

## Preferred Voice

- Japanese, first-time-reader friendly, technically precise.
- Begin with a recognizable engineering problem, then state what the article does.
- Use short paragraphs with one point each.
- Explain why a setting exists before listing syntax.
- Use concrete examples after abstract definitions.
- Make comparisons explicit: A was compared with B, B is a valid reference because C, and the difference was D.

## Minimal Gutenberg Patterns

Paragraph:

```html
<!-- wp:paragraph -->
<p>本文</p>
<!-- /wp:paragraph -->
```

Heading 2:

```html
<!-- wp:heading {"className":"wp-block-heading"} -->
<h2 class="wp-block-heading">見出し</h2>
<!-- /wp:heading -->
```

Heading 3:

```html
<!-- wp:heading {"level":3,"className":"wp-block-heading"} -->
<h3 class="wp-block-heading">小見出し</h3>
<!-- /wp:heading -->
```

Code:

```html
<!-- wp:code -->
<pre class="wp-block-code"><code>cmake --build build_test -j2</code></pre>
<!-- /wp:code -->
```

Unordered list:

```html
<!-- wp:list {"className":"wp-block-list"} -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>項目</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
```

Image marker:

```html
<!-- 画像挿入候補: メッシュ全体と固定面が分かる図。alt案: FrontISTR解析モデルのメッシュと固定面 -->
```

## Common Failure Modes

- Converting Markdown mechanically and losing explanatory examples.
- Leaving Markdown backticks in HTML paragraphs.
- Using h4 or h5 because the source document has deep nesting.
- Numbering headings and later leaving stale references such as `手順2`.
- Claiming an install or calculation succeeded when only commands were documented.
- Describing `build_test`, build target `fistr1`, and executable `fistr1/fistr1` as the same thing.
- Showing a result image without explaining what quantity, unit, scale, and conclusion the reader should inspect.
- Writing "this is not only X" before introducing X, which assumes a prior question the new reader never saw.
