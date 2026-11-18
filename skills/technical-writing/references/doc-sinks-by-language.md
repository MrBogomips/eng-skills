# What gets published, per language

A documentation tool or an API framework copies some comments and strings into published documentation. Those are
user text. Everything else in the source is contributor text.

| Language | Published (user text) | Safe for project references |
|---|---|---|
| C#, F#, VB | `///` XML comments: IDE tooltips, the package's XML doc file, OpenAPI via XML comments; `WithSummary`, `WithDescription`, `[Description]`, `[SwaggerOperation]` | `//` |
| Java, Kotlin, Scala, Groovy | `/** */` (Javadoc, KDoc); `@Operation`, `@Schema`, `@Parameter`, `@ApiResponse` strings | `//`, `/* */` |
| TypeScript, JavaScript | `/** */` (TSDoc, JSDoc; kept in `.d.ts`); `/*! */` (kept by minifiers); `@ApiOperation`, `@ApiProperty` strings | `//`, `/* */`; shipped source maps carry every comment |
| Python | Docstrings of modules, public classes and functions (Sphinx, `help()`, FastAPI uses them as operation descriptions); `summary=`, `description=` | `#` |
| Go | Any comment block **directly above** an exported name, an exported field, or the `package` clause | Inside the function body, or separated from the declaration by a blank line |
| Rust | `///`, `//!`, `/** */`, `/*! */` | `//` |
| Swift | `///`, `/** */` | `//` |
| PHP | `/** */` (phpDocumentor) | `//`, `#` |
| OpenAPI, AsyncAPI, GraphQL SDL, proto | The **whole file**: descriptions, YAML `#` comments, `x-` extensions, file name | Nowhere in a file published as it is. Keep references in the spec, ADR or PR, or in a source file that a build filters before publishing |
| Markdown and other doc pages | Whole file when it is published (manual, guide, release notes) | Contributor pages only (`CONTRIBUTING.md`, design notes) |

## Notes

- **`@internal`, `@hidden`, `stripInternal`** remove a whole declaration from generated docs. They do not hide one
  reference inside a published comment. Don't use them for this.
- **Go**: `// FR-112: ...` placed above `func Cancel` becomes the first line of its godoc. Move it into the body.
- **Python**: FastAPI uses the docstring as the operation description when `description=` is absent, so the
  endpoint's docstring is in the OpenAPI document.
- **C#**: a reference that must sit above the declaration goes in a `//` line before the `///` block.
- **Multi-line API metadata** (`.WithDescription("..." + "...")`) is published in full, continuation lines included.
- **When in doubt**, treat the text as published. Moving an ID into an implementation comment costs nothing.
