# historic_artefacts

Historic artefacts of the InterMine project, kept for users who ask for old data that is no longer available from a live mine after a rebuild or upgrade. Each artefact lives in its own directory, with one sub-directory per export date.

## Contents

### humanmine-public-lists/2026-11-17

All public lists of the live HumanMine as of 17 November 2026.

- HumanMine release (`/service/version/release`): 12 February 2022
- InterMine version (`/service/version/intermine`): 5.0.8
- 184 lists (16,463 members in total): 181 Gene lists, 2 Protein lists, 1 SNP list.
- 171 of them are Genomics England PanelApp gene panels (`PL_GenomicsEngland_GenePanel:*`). They hold the Green genes only, with panels as of December 2021 according to the list descriptions.
- The other 13 lists (`PL_*`) were contributed by other groups and are described in their list descriptions.

Files:

- `lists.json`: raw answer of `/service/lists?format=json` (name, title, description, type, size, dateCreated, timestamp, tags, authorized, ...).
- `lists.tsv`: one row per list (name, type, size, dateCreated, title, description; tabs and newlines in the description collapsed to spaces).
- `members/<list name>.tsv`: members of each list, with a header row. The file name is the list name with `/` and whitespace replaced by `_` and `:` replaced by `__` (a colon is not allowed in Windows file names); `INDEX.tsv` maps file names back to list names. Gene lists: `Gene.primaryIdentifier`, `Gene.symbol`, `Gene.secondaryIdentifier`, `Gene.organism.name`. Protein lists: `Protein.primaryAccession`, `primaryIdentifier`, `symbol`, `name`, `organism.name`. SNP list: `SNP.primaryIdentifier`, `secondaryIdentifier`, `symbol`, `name`, `organism.name`. Empty values appear as `""`, as returned by the service.
- `members/INDEX.tsv`: file name, list name, rows exported.
- `export.log`: every request and its row count, plus any size mismatch. Member queries are POSTs to `/service/query/results`; the list name is in the request body, so it is logged beside the URL.

Verification: 184 member files for 184 lists, 16,463 exported rows equal to the sum of the list sizes, no per-list mismatches, no empty lists.

## Export method

The export reads the public web service only (no login, read-only). For each list the script queries `/service/query/results` with an `IN` constraint on the list name and the view for the list's type, requesting TSV. Requests are sequential with a 0.3 s pause. To refresh the archive:

    python3 -I scripts/export_humanmine_public_lists.py https://www.humanmine.org/humanmine/service humanmine-public-lists/<YYYY-MM-DD>

The script uses the Python 3 standard library only.

## Licence and provenance

The PanelApp gene panels are public data derived from Genomics England PanelApp (https://panelapp.genomicsengland.co.uk/). See the PanelApp terms for the conditions of reuse; no licence is asserted here. The other lists are public lists of the HumanMine; see their descriptions in `lists.tsv` for their sources.
