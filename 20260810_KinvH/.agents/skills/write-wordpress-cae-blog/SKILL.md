---
name: write-wordpress-cae-blog
description: Create or revise Japanese CAE, simulation, OpenFOAM, FrontISTR, FEM, CFD, build, and source-code tutorial articles as WordPress Gutenberg block HTML. Use this skill whenever the user asks for a blog article, WordPress-ready HTML, an SEO title, a technical tutorial, publication-ready documentation, or conversion of Markdown/analysis notes into a blog, even if they only say "記事にして" or "ブログ用". Inspect local source files and results, propose multiple SEO titles, use the recommended title as the HTML filename, leave image insertion markers, and write for first-time readers.
---

# Write WordPress CAE Blog

Create a technically grounded Japanese article that can be pasted directly into the WordPress code editor.

## Read The Reference

Read [references/style-and-template.md](references/style-and-template.md) before writing or substantially revising an article. When the original sample files are accessible, inspect the paths listed there as well.

## Workflow

1. Identify the article subject, target reader, working directory, source files, commands, results, and validation evidence from the conversation and local files.
2. Inspect the relevant inputs, scripts, source code, logs, and numerical outputs. Do not write technical claims from filenames alone.
3. Separate these states explicitly:
   - actually executed and verified;
   - implemented but not executed;
   - recommended as a reproducible procedure;
   - not yet verified or outside the current scope.
4. Propose 5 to 10 Japanese SEO title candidates before or alongside the article. Put the strongest search phrase near the beginning and mark one as recommended.
5. If the user has not selected a title, use the recommended title. Save the article as `[recommended title].html`. Remove only filename-invalid characters; preserve useful Japanese SEO terms.
6. Write Gutenberg block HTML without `html`, `head`, or `body` wrappers so the entire file can be pasted into WordPress's code editor.
7. Validate facts, heading levels, block pairing, HTML escaping, code blocks, and output paths before finishing.

## Required Deliverables

Create these files in the requested `docs` directory unless the user specifies another location:

- `SEOタイトル案.md`: title candidates, the recommended title, target keywords, and a short reason for the recommendation.
- `[recommended title].html`: complete WordPress block HTML.

When revising an existing HTML article, preserve its filename unless the user asks for a rename. Update `SEOタイトル案.md` only when title work is part of the request.

## Article Structure

Adapt the sections to the subject, but normally use this order:

1. Greeting and a concrete problem the reader recognizes.
2. A short statement of what was achieved or investigated.
3. A highlighted `この記事でわかること` box.
4. Intended reader and environment when useful.
5. Purpose and physical or engineering position of the calculation.
6. Model, assumptions, units, and folder structure.
7. Commands and settings in the order actually used.
8. Explanation of what each important command, keyword, variable, and source location does.
9. Results and validation: state what was compared with what, why the comparison is valid, and the numerical difference.
10. Problems encountered and their causes.
11. Interpretation, limitations, applications, and summary.

Start from the reader's question. Do not write sentences that only make sense as answers to an invisible previous conversation. Introduce every symbol and term before contrasting it with something else.

## WordPress HTML Rules

- Use only heading levels 2 and 3: `<h2>` and `<h3>`. Never emit `<h1>`, `<h4>`, `<h5>`, or `<h6>`.
- Do not number headings. Refer to a section by its title instead of "手順2" or "第3章".
- Wrap every paragraph, list, heading, table, and code block in matching Gutenberg block comments.
- Use `<code>` for inline paths, commands, keyword names, and identifiers.
- Use `<pre class="wp-block-code"><code>...</code></pre>` for multiline code and escape `&`, `<`, and `>` inside code.
- Use standard Gutenberg lists and tables. Keep tables narrow enough to read on mobile.
- If the article contains formulas, put the MathJax shortcode block at the top and use `$...$` for inline math and `$$...$$` for display math.
- Do not place Markdown backticks, Markdown headings, or fenced code blocks in the HTML output.
- Do not add a duplicate article title as an `<h1>`; WordPress supplies the post title separately.

Use a highlighted box when it improves scanning:

```html
<!-- wp:jin-gb-block/box-with-headline {"boxTitle":"この記事でわかること"} -->
<div class="wp-block-jin-gb-block-box-with-headline kaisetsu-box1"><div class="kaisetsu-box1-title">この記事でわかること</div><!-- wp:list {"className":"wp-block-list"} -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>項目</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list --></div>
<!-- /wp:jin-gb-block/box-with-headline -->
```

## Image Handling

The user adds images in WordPress later. Do not invent media IDs or URLs and do not create broken `<img>` tags. Leave a harmless HTML comment at the best insertion point:

```html
<!-- 画像挿入候補: ParaViewで表示した変位分布。本文では最大変位と変形方向を説明する -->
```

Place a normal WordPress paragraph before or after the marker that explains what the future image should show. Use descriptive Japanese alt-text suggestions in the comment when helpful.

## Technical Writing Rules

- Write for a reader using the software for the first time.
- Explain the purpose before the setting.
- Explain a command immediately after showing it. Cover paths, options, expected output, and success criteria.
- For source changes, state the repository-relative file path, procedure or function name, insertion point, and physical role.
- For calculations, define symbols, dimensions, units, boundary conditions, and assumptions.
- Use bullet lists for groups of settings and tables for comparisons.
- Distinguish a directory, source file, build target, executable, and installed executable. Do not use them interchangeably.
- Explain abbreviations such as RHS, DOF, MPI, CHT, and FEM on first use.
- Avoid unsupported certainty. If a result was not run, say so.
- Avoid filler, promotional exaggeration, and unexplained jargon.

## SEO Title Rules

Generate title candidates with different search intents:

- direct procedure: `FrontISTRで...する手順`;
- beginner intent: `初心者向け` or `入門`;
- troubleshooting intent: `エラー原因と対処`;
- detailed reference intent: `徹底解説`;
- outcome intent: include the concrete file, solver, keyword, or result.

Prefer specific product and feature names such as `FrontISTR`, `OpenFOAM`, `fstr_main`, `CMake`, `温度荷重行列H`, or `熱膨張`. Avoid titles that promise more than the article proves.

## Validation

Before finishing, check:

- only `<h2>` and `<h3>` heading tags exist;
- heading block `level` values are absent for h2 or equal to 3 for h3;
- Gutenberg opening and closing block counts match;
- `<pre>` and `<code>` opening and closing counts match;
- no raw Markdown backticks remain outside code content;
- no `TODO`, fake image URL, fabricated media ID, or invisible conversational premise remains;
- commands and paths exist when local access permits;
- stated numerical comparisons are supported by files or logs;
- the output filename matches the selected SEO title.

Summarize the created files and any unverified points in the final response.
