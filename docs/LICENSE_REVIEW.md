# License review record

Reviewed on 2026-09-28 against
[27e1ad14fed36a942b8ca315c3113bb167f48ea3](https://github.com/saintshamanix/lazyproxy/tree/27e1ad14fed36a942b8ca315c3113bb167f48ea3),
before adding the MIT license and notices.

## Scope and evidence

- Inventoried all 49 tracked files in the GitHub tree, including hidden workflow
  files, shell/Python implementation, templates, tests and documentation.
- Matched local Git blob hashes to the published tree: 47 files matched exactly.
  The two README files were read directly from the pinned GitHub revision and
  used as the baseline for the documentation edits.
- Inspected download paths, license/copyright references, the decoy HTML/JavaScript
  and routing profile. No bundled upstream source tree, binary, image or webfont
  was found. The decoy uses no third-party JavaScript library.
- Reviewed local construction scripts and the recorded upstream integration
  references. Compared implementation/template/test text against the reviewed
  x-ui-pro script and 3x-ui 3.8.5 source: 1,260 reference files; no matching
  contiguous blocks of eight nonempty, whitespace-trimmed lines totaling at
  least 160 characters were found.
- The owner confirmed authorship of the INCY rules selection and explicitly
  authorized publication under MIT.
- Checked the GitHub releases collection: no published releases were listed at
  review time.
- Checked upstream license texts and documented separately downloaded software
  and remote data in [THIRD_PARTY.md](../THIRD_PARTY.md).

## Result and limits

The review found no identified bundled third-party material requiring an
exception to MIT for the current LazyProxy files. The previous license placeholder
is replaced with the standard MIT text, naming the repository owner's GitHub
handle, `saintshamanix`.

This is a repository-scoped provenance review, not proof of worldwide originality
or an exhaustive audit of upstream transitive dependencies. Text comparison cannot
exclude shorter or modified passages. Separately downloaded components and
datasets are not relicensed. Future contributions, vendored files and binary
distributions require their own provenance and license review.

No installer behavior, firewall rules or server configuration changed as part
of this licensing update.
