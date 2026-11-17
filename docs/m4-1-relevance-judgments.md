# M4.1 Manual Relevance Judgments

## Corpus and review method

The only answerable source used for this evaluation is
`STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf`, represented by 294
processed chunks covering pages 2–23. Each label below was established by
reading the source chunk text and confirming that it contains direct evidence
for the question. Chunk IDs and pages are retained exactly as stored in the
processed JSON.

These are verified evidence labels, but not an exhaustive independent
annotation of every one of the 294 chunks for every question. Consequently,
recall in the generated results is reported as
`recall_status=provisional_manual_set`; it must not be interpreted as
full-corpus recall.

## Answerable labels

| Question | Relevant chunk IDs (page) | Evidence scope |
|---|---|---|
| M41-Q001 | `de043ef96a8ae1f6` (2) | Application inside and outside campus |
| M41-Q002 | `de043ef96a8ae1f6` (2) | Peaceful protest and prior intimation |
| M41-Q003 | `de043ef96a8ae1f6` (2), `407ea400e4a6bc87` (2) | Good conduct, orderly behaviour, academic environment |
| M41-Q004 | `f6901e6afc25a826` (2) | Vice-Chancellor discipline authority |
| M41-Q005 | `de043ef96a8ae1f6` (2) | Scope for all students and commencement timing |
| M41-Q006 | `067e151abf58a54b` (6), `cd21ed39ea433e92` (6), `b9d4a0253e0c7079` (6) | Category I violence, coercion, and sexual-harassment examples |
| M41-Q007 | `ff10accb8ee6929c` (7) | Bullying and cyberbullying |
| M41-Q008 | `ff10accb8ee6929c` (7), `d75de57ebb19414a` (20) | Prohibited substances and statutory penalties |
| M41-Q009 | `d8fdccb230b145e7` (7), `52ddcdbb080cd9fa` (22), `de27a8ec20c10687` (22) | Gambling/betting and assistance |
| M41-Q010 | `611b52029bcb3803` (7) | Unauthorized guests in halls |
| M41-Q011 | `d8fdccb230b145e7` (7), `1bd03e260f92b3d0` (9) | Cooking and hostel equipment restrictions |
| M41-Q012 | `7669e7dae47cf2b3` (8), `b6786e460d8f24f9` (14), `4b1d6525b819fe8d` (14) | Unauthorized departure and penalties |
| M41-Q013 | `3a0f8860a52bc4a2` (8), `55e8087c88228ea2` (11), `535c148766e9b21a` (11) | Refusal or resistance to inspection |
| M41-Q014 | `4cc62505faa68f61` (23), `4fdfafc18b3d0fed` (23) | Identity card, access code, and app sharing |
| M41-Q015 | `ff10accb8ee6929c` (7), `a31ed4f0b92139ff` (22) | Discrimination and protected characteristics |
| M41-Q016 | `8995f95b4d376550` (3) | Complaint receipt and jurisdiction screening |
| M41-Q017 | `8995f95b4d376550` (3), `0cdb342f55dd0425` (3) | Statements, witnesses, and evidence |
| M41-Q018 | `0cdb342f55dd0425` (3) | Material evidence and veracity |
| M41-Q019 | `0cdb342f55dd0425` (3) | Charges, show-cause notice, and defence |
| M41-Q020 | `047e458c9fdc7f71` (5) | Ex parte conclusion when the accused fails to appear |
| M41-Q021 | `df3dfc8b2bc5d039` (4), `e1d1f1cadd1a923a` (4) | Notice, meeting, and recommendation timelines |
| M41-Q022 | `94dc298b1e4ee1aa` (3), `1c5dc37875e96455` (4) | Deputy Proctor screening and escalation |
| M41-Q023 | `1c5dc37875e96455` (4) | Serious/off-campus cases and University Committee |
| M41-Q024 | `1c5dc37875e96455` (4), `df3dfc8b2bc5d039` (4) | Investigator membership rule and exception |
| M41-Q025 | `df3dfc8b2bc5d039` (4) | Confidential custody of proceedings |
| M41-Q026 | `0320a43289fbdbe8` (8) | Category I punishments |
| M41-Q027 | `8fce4c0b6a83c0fd` (8), `895bb5ab0b064e1c` (9) | Category II punishments |
| M41-Q028 | `8fce4c0b6a83c0fd` (8), `c69573124c7ca1be` (11), `1096dc30c910dca8` (11) | Property damage/theft and sanctions |
| M41-Q029 | `4d05133a12ccb25e` (10), `fbf867d031fbe036` (10), `759eccd49a9822da` (10) | Alcohol/inebriation and escalating penalties |
| M41-Q030 | `9ee67371159ace93` (21), `0396efee68c45a18` (21), `66f41fbf883ec7a2` (15) | Violence, bodily injury, and penalties |
| M41-Q031 | `74b85be0218069f0` (5) | Written appeal and five-working-day deadline |
| M41-Q032 | `74b85be0218069f0` (5) | Review authority and Vice-Chancellor options |

## Unsupported labels

M41-Q033 through M41-Q040 have empty relevance sets. They ask about fees,
attendance, scholarships, examinations, room allocation, library overdue
fines, course registration, or dining prices. The current processed corpus
does not contain those procedures or facts. The scholarship PDF in
`data/input/` was intentionally not treated as evidence because it has not
been ingested or embedded.
