# Features
- [ ] Read pdf meta-data if present, and compare with filename
- [ ] Don't hard-code pattern substitutions, but use compiled regexp taken from `config.py`
- [ ] Don't override `.queried.json` on repeated queries (append instead).
- [ ] Use info from Crossref json to remove ambiguity in author names (first name / last name)
- [ ] Rename feature should also rename supplemental material, if present.
- [ ] Better/more consistent management of duplicated entries in `.queried.bib` and `.manual.bib` (don't query file which is present in `.manual.bib`)
- [ ] Check year against google scholar.
- [ ] Add a mode to enable/disable utf8 in resulting .bib
- [ ] Add functions to rename between different naming conventions
- [ ] Add a function to update the bibkeys in a .tex project (update the .bib as well as all the citations the .tex files of the project).

# Options
- [ ] -e: --eval bib (show diff dist between filenames and bib entry)
