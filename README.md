# anki-harness

An unofficial test harness for [Anki](https://github.com/ankitects/anki). It runs scripted
scenarios inside a real Anki, with no window, on several released versions, and reports where
a check fails or the versions disagree.

Not affiliated with or endorsed by Anki Software, LLC or AnkiHub. It installs Anki's own
published packages and drives them unmodified.

## Why

Anki's Rust core is well tested. The desktop interface and the web front end are covered far
less, and that is where users meet regressions: the editor, image occlusion, the review
screen. This harness drives those through the real application, the way a person does, so a
bug can be shown as a short script that anyone can run, and a new release can be compared
with the last one before people upgrade.

## Use

Needs Python 3 and [uv](https://docs.astral.sh/uv/). Tested on macOS (Apple silicon).

```sh
./install.sh 26.9.4          # once per version: a few hundred MB each, mostly Qt
./install.sh 26.11b1
python3 run.py               # every scenario on 26.9.4 and 26.11b1, about a minute
python3 run.py --versions 26.9.4,26.11b1 --scenarios review_keys
```

Each (version, scenario) pair runs in its own process on a throwaway profile folder. It never
opens your own Anki profile. `--collection PATH` starts from a copy of a collection file you
give it.

What it prints:

| Word | Meaning |
|---|---|
| `FAIL` | A check that must hold on every version did not hold |
| `DIFFERS` | An observation is not the same on every version. A lead, not a verdict: it may be a regression, a fix, or noise |
| `known #N still present` | A check tied to an open Anki issue still fails. Expected |
| `FIXED?` | A check tied to an open Anki issue now passes |
| `inconclusive` | The scenario's own control failed three times running. Nothing is concluded |

## What it covers

Last run 15 November 2026, on 26.09.4 and 26.11 beta 1.

| Scenario | What it drives | 26.09.4 | 26.11 beta 1 |
|---|---|---|---|
| `review_keys` | Review with real key presses: Space shows the answer, a number grades, Undo puts the card back | passes | passes |
| `io_multiselect_move` | Image occlusion in the browser's editor, with real mouse drags: move one mask (the control), then two selected together | the multi-selection move is not saved ([#4223](https://github.com/ankitects/anki/issues/4223)) | same |
| `io_thin_mask_narrow_pane` | An occlusion note with one mask 1% of the image wide. Move the other mask in a wide window (the control), then again with the note opened in a 260 px editor pane | the thin mask is deleted from the note in the narrow pane ([#3267](https://github.com/ankitects/anki/issues/3267)) | same |
| `io_small_mask_narrow_pane` | The same steps with a mask 1.5% of the image wide | the mask is kept | **the mask is deleted** |
| `overview_keys_undo` | Press R on an ordinary deck's overview after an undoable change | undo history is emptied ([#4311](https://github.com/ankitects/anki/issues/4311)) | same |
| `tag_redo` | Undo, then expand a tag | the pending redo is discarded ([#5965](https://github.com/ankitects/anki/issues/5965)) | same |

The issue numbers are bugs already reported to the Anki project by other people. They are
here as calibration: a harness that cannot see a bug known to be present is not evidence of
anything. Each scenario is a self-contained reproduction.

### The one difference between the versions

When the editor saves an occlusion note it drops any shape under 5 px wide or high, measured
on the canvas (`ts/routes/image-occlusion/shapes/to-cloze.ts`). The canvas takes its size
from the editor pane when the mask editor mounts. So an existing mask can fall under 5 px
simply because the note was opened in a narrow pane, and it is then removed from the note
the next time anything is edited, without a message.

In a 260 px pane, 26.09.4 draws the test image 431 px wide and 26.11 beta 1 draws it 213 px
wide, so the beta deletes masks about twice as large: up to 2.3% of the image width, against
1.2%. The only functional change to the mask editor between the two tags is
[#5803](https://github.com/ankitects/anki/pull/5803), which lets the mask editor's column
shrink to the window so the toolbar can scroll again. That change does what it says; the
smaller canvas is a side effect that widens #3267. Four runs, the same result each time.

Not tested here: the standalone image-occlusion page that the mobile apps use.

## How it works

- `harness/inproc.py` is the engine. The process is Anki itself: it starts `aqt` offscreen on
  a temporary base folder, waits for the collection, and steps a scenario on Qt's main
  thread. It exits without Anki's close-time sync or backup.
- A scenario (`harness/scenarios/<name>.py`) is a generator, `run(s)`. It yields a number
  (seconds to wait) or a function (wait until it returns true). Through the session `s` it
  reaches `s.mw` and `s.col`, sends real Qt key and mouse events (`s.key`, `s.mouse`),
  evaluates in any of Anki's web views (`s.js`), and records:
  - `s.observe(name, value)`: compared between versions;
  - `s.check(name, ok, detail)`: must hold on every version;
  - `s.check(..., known="#4311")`: tied to an open issue;
  - `s.inconclusive(reason)`: the scenario could not drive Anki; the runner tries again.
- Every web view is also reachable over the Chrome DevTools protocol
  (`HARNESS_CDP_PORT`), for Playwright or any other client. No scenario needs it yet.
- `run.py` runs the matrix and prints the table.

## Writing a scenario

- One scenario, one path a user takes.
- Put a control in the same run. If the control fails, call `s.inconclusive`; do not report
  the bug.
- Read positions fresh before each input, and retry an input until the page shows it
  landed. The image-occlusion editor does not keep masks in a fixed order and can miss a
  drag while its layout settles.
- Keep observations small and repeatable: no timestamps, no ids, numbers rounded.
- A timing difference means nothing unless it survives alternating runs on an idle machine.

## Not covered yet

In the order planned: the note editor (legacy and new), the browser (search, flags, preview,
find and replace), import and export through the real pages, deck options and the FSRS
pages, statistics, starting from a large real collection, random operation sequences with
undo and redo invariants, popular add-ons loading on a new version, Anki's `main` built from
source, Linux and Windows, and a scheduled run in CI.

## Notes

- Anki 25.09 needs `QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu` offscreen (the default here).
  Its number keys do not grade under the harness; unexplained, and not pursued on an old
  version.
- Written with AI assistance (Claude). Every scenario is run against the released Anki
  builds it names before it is committed.

## Licence

AGPL-3.0-or-later, the same as Anki, whose code the scenarios import.
