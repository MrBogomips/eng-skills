# Release notes and changelogs

## Release notes (for users)

Release notes tell users **what changes for them**. Build them from commits, PRs and tickets, but don't copy those.

Order:

1. **Breaking changes**, first. For each: what stops working, what to use instead, and the action to take before
   upgrading.
2. **New**, **Improved**, **Fixed**, **Deprecated**: one line each, phrased as user impact ("Invoice totals are now
   rounded to 2 decimals"). Not as the code change ("fix rounding in TotalsCalculator").

Leave out changes users can't observe: refactoring, CI, dependency bumps, migrations, infrastructure moves. Mention
an internal change only through its effect, when users notice it ("Invoice lists load faster").

Never include:
- tracker keys, story or requirement IDs;
- issue numbers (unless the tracker is public and the link helps the user);
- code names, internal service, host or cluster names;
- commit hashes, author names.

**Missing facts.** A breaking change with no known replacement, a migration step nobody wrote down, a removal date
nobody decided: ask the user. If you can't, publish what is known and list the gaps in your reply. Never write
"migrate to the supported alternative" without naming it.

## Changelog (for integrators and contributors)

A changelog in the repository (for example in the Keep a Changelog format, with an `Unreleased` section) follows
the same wording rules if it is published with the product. It may link public issues. Internal tracker keys stay
in commits and PRs.

## Commit and PR titles

When the project generates release notes from commit or PR titles, those titles are user text: write them as user
impact, and put tracker keys in the body or a trailer, not the title.
