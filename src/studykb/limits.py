"""Every hardcoded number that is not a tuning knob, in one place.

Three kinds of threshold exist in this codebase and only two of them live here:

* what gets **indexed** — trigger characters, the graphics floor, chunk size,
  how many hits retrieval returns — is in ``config/default.yaml``;
* what makes a review check read **green or amber** is in that file too, under
  ``review:``;
* what is left is presentation, and it is below: how many items a report lists
  before it stops, how much of a passage it prints, how long an error excerpt
  is. None of it changes what is indexed or what a check decides.

The last section is different and says so.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# How many items a list prints before it truncates
# --------------------------------------------------------------------------
# Cosmetic only. The count printed next to each list is always the full one, so
# raising these shows more without changing any number you are reading.
UNASSIGNED_LISTED = 20        # `ingest`: sources no rule could place
VANISHED_LISTED = 10          # `ingest`: sources recorded but missing from disk
NO_CHUNKS_LISTED = 3          # SUMMARY.md: sources indexed nowhere
LOST_PAGES_LISTED = 3         # SUMMARY.md: sources that dropped a page with text
MISSING_LOCATORS_LISTED = 6   # SUMMARY.md: locators named inside one of those
EMPTY_PAGES_LISTED = 12       # extraction.md: pages that extracted to nothing
TINY_CHUNKS_LISTED = 8        # chunks.md: chunks under the tiny-chunk threshold

# --------------------------------------------------------------------------
# How much text a report prints
# --------------------------------------------------------------------------
SOURCE_COLUMN_WIDTH = 34      # `review`: source column in the terminal table
EXTRACTION_PREVIEW = 400      # extraction.md: opening characters of each page
CHUNK_OPENS = 110             # chunks.md: characters at the start of a seam
CHUNK_CLOSES = 70             # chunks.md: characters at the end of a seam
CHUNK_SEAM_MIN = 180          # below this a chunk prints whole, with no seam
RETRIEVAL_PASSAGE = 220       # retrieval.md: characters of each hit
RETRIEVAL_TITLE = 40          # retrieval.md: characters of its source title
RETRIEVAL_K = 5               # hits per query when queries.yaml sets no `k`
SEARCH_PASSAGE = 1200         # what `kb_search` sends an agent, per hit

# Rows scanned at the top of the timetable before giving up on finding the
# header. The real one has never been below row 5.
HEADER_SCAN_ROWS = 20

# --------------------------------------------------------------------------
# Error excerpts
# --------------------------------------------------------------------------
OCR_STDERR_TAIL = 500         # tail of ocrmypdf's stderr kept in the error
VISION_ERROR_HEAD = 200       # head of a caption failure stored on the Unit

# --------------------------------------------------------------------------
# Identity — changing these orphans work that already exists
# --------------------------------------------------------------------------
# These are not display widths. They are the length of keys that are already
# written into state.db and into filenames under the work directory.
#
# Change FINGERPRINT_CHARS and every stage of every source reruns, because no
# stored fingerprint matches any more — hours of OCR, captioning and embedding.
# Change either WORK_ name and the files the last run wrote become unreachable
# under their new names, so they are recomputed and the old ones stay on disk
# forever. There is no reason to touch any of the three.
FINGERPRINT_CHARS = 12
WORK_SHA_CHARS = 16
WORK_STEM_CHARS = 60

# Same idea, lower stakes: the folder a caption's page images are rendered into.
# Changing it renames those folders, so the next review re-renders every page
# and the old PNGs stay behind.
SLUG_CHARS = 60
