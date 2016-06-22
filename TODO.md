# Features
- [ ] Read pdf meta-data if present, and compare with filename
- [ ] Don't hard-code pattern substitutions, but use compiled regexp taken from `config.py`
- [ ] Don't override `.queried.json` on repeated queries (append instead).
- [ ] Use info from Crossref json to remove ambiguity in author names (first name / last name)
- [ ] Rename feature should also rename supplemental material, if present.

# Options
- [ ] -e: --eval bib (show diff dist between filenames and bib entry)
