"""
Fetch metadata from DOIs in the database.

- Option -r to recurse (apply to subfolders).
- Option to specify providers (crossref/arxiv/google)
- Read input from a .txt with list of doi/titles.

Identify DOIs + metadata information.

- Guess from PDFs (either binary content or use filename) in current folder.
- Read input queries from a .txt file + optional pattern to match.
- Read input queries from a .bib file.

For providers such as crossref, a list of choices is given, and user needs to pick 1 answer.
"""