# Armenian inscriptions — data

Structured inscription notices extracted from the *Corpus Inscriptionum
Armenicarum* by a vision-language model, together with the corrections
researchers have made to them.

## What is here

| | |
|---|---|
| `notices.jsonl` | the machine extraction, one notice per line |
| `corrections/<id>.json` | human corrections, one file per notice |

**The extraction is never overwritten.** A correction shadows it, so
*what did the model produce* stays answerable for every field, forever.
`notices.jsonl` is rebuilt wholesale from the extraction pipeline; nothing in it
is hand-edited.

## Correcting a notice

Use the proofreading interface — it shows the catalogue page beside the
transcription and writes the correction in the form this repository expects.
Press **Propose this notice on GitHub** and it opens a pre-filled issue. You
need a GitHub account; the site will prompt you to sign in or register.

A workflow then validates the issue and commits the correction, crediting you as
co-author. It refuses rather than guesses: an unknown notice, a field that is not
correctable, a crop box outside the page, or a transcription whose diplomatic
brackets do not balance is rejected with an explanation.

## Diplomatic notation

Transcriptions are diplomatic. These marks are data, not formatting, and are
preserved exactly:

| mark | meaning |
|---|---|
| `⎡ ⎤` | letters restored by the editor |
| `⎣ ⎦` | an error or omission on the stone |
| `[ ]` | extraneous characters |
| `...` | letters destroyed, count unknown |
| `/` | a line boundary on the stone |

Do not modernise the Armenian, normalise the characters, or replace these
brackets with ordinary parentheses.

## Images

Page scans are not in this repository — they are served separately; see the project notes.
