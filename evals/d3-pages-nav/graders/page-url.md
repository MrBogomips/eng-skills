---
type: regex
pattern: "https://example\\.github\\.io/pixkit/guides/batch/"
match: contains
target:
  source: file
  path: DOCS-IMPACT.md
---
The report gives the published URL of the new page, derived from site_url and the default MkDocs directory URLs.
