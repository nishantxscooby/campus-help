# Independent review of discipline rules

The manifest contains 12 leads from the indexed discipline handbook. All are pending. Each quotation is the original chunk slice with layout whitespace preserved. The parent appears uniquely on its cited PDF page after whitespace normalization. The shared document identity and two SHA-256 digests apply to every entry. The stored section label comes from extraction and may be misleading.

The original authority verifier requires one complete parent in the exact form `{actor} may {action} {object} under {scope}.`. Zero of the 294 indexed parents match even the necessary “may … under …” structure. The ten conduct entries rely on the misconduct list heading. The two authority passages use different wording and occupy only part of their parent. An independent review can confirm what these passages say, but approving a lead alone cannot enable it. The example review questions describe possible future coverage.

| Proposed ID | Open the PDF | Proposed question |
|---|---|---|
| discipline-promulgation | [Page 4](../data/input/STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf#page=4) | Who issues the promulgation orders? |
| discipline-major-review | [Page 5](../data/input/STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf#page=5) | Who reviews major penalties on appeal? |
| discipline-false-certificates | [Page 6](../data/input/STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf#page=6) | Is furnishing false information to the University listed as misconduct? |
| discipline-unauthorized-entry | [Page 6](../data/input/STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf#page=6) | Is colluding in unauthorized entry into campus listed as misconduct? |
| discipline-gambling | [Page 6](../data/input/STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf#page=6) | Is gambling on University premises listed as misconduct? |
| discipline-intoxicants | [Page 6](../data/input/STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf#page=6) | Is possessing dangerous drugs on University premises listed as misconduct? |
| discipline-property | [Page 7](../data/input/STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf#page=7) | Is defacing University property listed as misconduct? |
| discipline-tour | [Page 7](../data/input/STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf#page=7) | Is improper behavior on an official university tour listed as misconduct? |
| discipline-ragging | [Page 7](../data/input/STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf#page=7) | Is ragging listed as misconduct? |
| discipline-guests | [Page 7](../data/input/STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf#page=7) | Is accommodating unauthorized guests in halls of residence listed as misconduct? |
| discipline-intimidation | [Page 7](../data/input/STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf#page=7) | Is intimidating a staff member listed as misconduct? |
| discipline-cooking | [Page 7](../data/input/STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf#page=7) | Is cooking food in hostel rooms listed as misconduct? |

## Record a decision

1. Open the linked PDF page. Find the quotation in [the manifest](discipline-review.json) using its first words. Verify the visible punctuation, item number and surrounding text. Compare the exact quotation to the half-open character slice in the indexed JSON. The automated check for offsets, page, complete unit and source digests is `python -m pytest tests/test_review_release.py -k real_review`.
2. Read the preceding and following provisions, the applicability rules on page 2, any governing definitions and exceptions, and related provisions elsewhere in the document. For example, page 5 assigns minor and major penalty reviews separately. For list items on pages 6–7, inspect the heading on page 6. Test both questions in the manifest. Record what the quotation establishes, its limits and any conflicts. A null conditions or exceptions field means unknown.
3. On a copy of the manifest, record the decision as APPROVED or REJECTED, the reviewer's identity, ISO decision date, review revision and rationale alongside each fact ID. Retain the original source digests and the signed-off copy through the operator's normal review channel. Leave unresolved items PENDING_REVIEW. An APPROVED source reading may still be ineligible for the web verifier.
4. For independently approved facts within the supported authority form, prepare an operator release using the schema below. The release is a complete snapshot. Keep pending and rejected records inactive, use a unique stable ID per candidate and record decisions against the exact source version. A source change requires a fresh review. Conditions, exceptions, conflicts or required governing provisions block an answer. Only record empty lists after checking those properties. Confirm that the scoped question has one possible authority and that the whole quoted parent establishes it.
5. The operator obtains the release SHA-256 from the independent review channel and configures the file and digest together before restarting FastAPI. Whoever controls both settings is trusted to authorize releases. The digest checks file identity; it cannot authenticate a person. For revocation, replace the release with the newly reviewed snapshot and pin, then restart all workers.

## Operator release format

Generate the exact JSON Schema from the repository root:

```bash
python -c 'import json; from campus_help.web.reviews import Release; print(json.dumps(Release.model_json_schema(), indent=2))'
```

The envelope contains the document filename, PDF and corpus SHA-256, review revision, relation, modality, polarity, scope completeness, conditions, exceptions, conflicts, definitions, governing provisions and entries. Each entry supplies status, decision date, reviewer, actor, action, object, scope and a complete witness. Dates use YYYY-MM-DD. Copy citation coordinates from the canonical parent. The checked-in synthetic example builder is in [review_fixture.py](../tests/review_fixture.py). Its source and approvals are fictional.

```bash
export CAMPUS_HELP_REVIEW_FILE=/path/to/reviewed-release.json
export CAMPUS_HELP_REVIEW_SHA256='REPLACE_WITH_REVIEWED_SHA256'
python -m uvicorn campus_help.web.api:app --host 127.0.0.1 --port 8000
```

Replace both placeholders before running. With neither setting, the service uses the bundled handbook and an empty registry. Invalid configuration prevents startup. A changed PDF or citation blocks answers. Pending review leads live outside the runtime registry.

## Enable the first reviewed appeal answer

1. Copy [the focused passage release](discipline-passages.json) to a separate review file. Keep the six source records and their source pins together. Use the `appeal` entry for the first review. Open [PDF page 5](../data/input/STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf#page=5) and inspect all of section 6.
2. Independently check the entire proposed claim and every listed question against clause i. Check eligibility, procedure, recipient, number, unit, triggering event, governing provisions and exceptions. Check that the major/minor review clauses answer different questions. Compare the exact text and offsets of both witnesses. Record any conflict in `conflicts`. Leave the entry pending or reject it if the evidence is insufficient.
3. For a supported entry only, record the reviewer’s actual identity and ISO decision date, replace the provisional `exceptions` text with the review finding, record a new `review_revision`, set `review_complete` to true and `status` to APPROVED. Include applicable limits in the approved claim and quotations. Leave every other decision pending. Submit the complete release bytes and their SHA-256 through the independent review channel.
4. Set `CAMPUS_HELP_REVIEW_FILE` to that file and `CAMPUS_HELP_REVIEW_SHA256` to the independently supplied digest. Restart FastAPI with the README command. Ask “What is the deadline to file an appeal?” and inspect both citations. Ask “Does my appeal deadline start from the incident?” and check that it produces no confirmed answer.

The focused release uses original chunk offsets for clauses and PDF page text offsets for headings missing from the chunks. The digest of the text between the first and last quotation binds their relationship to this version of the page. Page-level coordinates refer to PyMuPDF plain text. Every record is limited to one page. Table cell associations and student debarment have no approved coverage.
