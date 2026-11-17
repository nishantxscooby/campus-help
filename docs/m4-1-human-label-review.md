# M4.1 Human Label Review Worksheet

## Instructions

This worksheet audits, but does not change, the labels in `data/evaluation/m4_1_questions.json`. Every entry is initially marked `PENDING_HUMAN_REVIEW`. Reviewers should confirm whether each quoted chunk directly supports the exact question, add or remove labels only in a separate approved revision, and record the decision outside this pending worksheet.

Source corpus: `data/output/discipline-rules.json`, 294 chunks from `STUDENTS-DISCIPLINE-AND-CONDUCT-RULES_compressed.pdf`. Source text below is copied from the processed JSON; line breaks are preserved.

## Answerable questions

### M41-Q001: Do the discipline rules apply if a student commits misconduct outside the university campus?

- **Category:** `conduct_responsibilities`
- **Current relevant chunk IDs:** `de043ef96a8ae1f6`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 2: breaches inside or outside campus fall under the rules.

#### Labelled source evidence

**Chunk `de043ef96a8ae1f6` — page 2, section `2. APPLICATION OF RULES`**

```text
1. These rules are not meant to deny the democratic rights of the students to dissent/air their

grievances/protest in a peaceful manner.

2. Peaceful sit-ins/dharanas at a designated place with prior intimation to the university

administration will not invite any punishment under these rules.

3. These Rules shall apply to all students of the University (including parttime students)

whether admitted prior to the commencement of these Rules or after the commencement of

these Rules.

4. Any breach of discipline and conduct committed by a student inside or outside the University

Campus shall fall under the purview of these Rules.

3. Code of Conduct: The Code of Conduct for students shall include:

i.

Observance of good conduct and orderly behavior within or outside the campus.

ii.

Emulating healthy traditions of the University and developing as responsible students at

the University.

iii.
```

**Why it appears relevant:** Verified on page 2: breaches inside or outside campus fall under the rules.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q002: Can students hold a peaceful sit-in or dharna without being punished under these rules?

- **Category:** `conduct_responsibilities`
- **Current relevant chunk IDs:** `de043ef96a8ae1f6`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 2: a designated peaceful sit-in with prior intimation does not invite punishment.

#### Labelled source evidence

**Chunk `de043ef96a8ae1f6` — page 2, section `2. APPLICATION OF RULES`**

```text
1. These rules are not meant to deny the democratic rights of the students to dissent/air their

grievances/protest in a peaceful manner.

2. Peaceful sit-ins/dharanas at a designated place with prior intimation to the university

administration will not invite any punishment under these rules.

3. These Rules shall apply to all students of the University (including parttime students)

whether admitted prior to the commencement of these Rules or after the commencement of

these Rules.

4. Any breach of discipline and conduct committed by a student inside or outside the University

Campus shall fall under the purview of these Rules.

3. Code of Conduct: The Code of Conduct for students shall include:

i.

Observance of good conduct and orderly behavior within or outside the campus.

ii.

Emulating healthy traditions of the University and developing as responsible students at

the University.

iii.
```

**Why it appears relevant:** Verified on page 2: a designated peaceful sit-in with prior intimation does not invite punishment.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q003: What general behaviour does the student code of conduct expect?

- **Category:** `conduct_responsibilities`
- **Current relevant chunk IDs:** `de043ef96a8ae1f6`, `407ea400e4a6bc87`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 2: good conduct, orderly behaviour, healthy traditions, and attention to academic work.

#### Labelled source evidence

**Chunk `de043ef96a8ae1f6` — page 2, section `2. APPLICATION OF RULES`**

```text
1. These rules are not meant to deny the democratic rights of the students to dissent/air their

grievances/protest in a peaceful manner.

2. Peaceful sit-ins/dharanas at a designated place with prior intimation to the university

administration will not invite any punishment under these rules.

3. These Rules shall apply to all students of the University (including parttime students)

whether admitted prior to the commencement of these Rules or after the commencement of

these Rules.

4. Any breach of discipline and conduct committed by a student inside or outside the University

Campus shall fall under the purview of these Rules.

3. Code of Conduct: The Code of Conduct for students shall include:

i.

Observance of good conduct and orderly behavior within or outside the campus.

ii.

Emulating healthy traditions of the University and developing as responsible students at

the University.

iii.
```

**Why it appears relevant:** Verified on page 2: good conduct, orderly behaviour, healthy traditions, and attention to academic work.

**Chunk `407ea400e4a6bc87` — page 2, section `Giving undivided attention to their academic work and maintaining a healthy and`**

```text
congenial academic environment in the University.

4. Acts of Indiscipline and Misconduct: Any act of misconduct committed by a student inside or

outside the campus, which is formally reported, shall be construed as violation of discipline of

the University. Without prejudice to the generality of the foregoing provision, violations of the

discipline shall include:
```

**Why it appears relevant:** Verified on page 2: good conduct, orderly behaviour, healthy traditions, and attention to academic work.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q004: Who has authority over student discipline and disciplinary action at Bennett University?

- **Category:** `conduct_responsibilities`
- **Current relevant chunk IDs:** `f6901e6afc25a826`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 2: the Vice Chancellor is vested with the relevant powers.

#### Labelled source evidence

**Chunk `f6901e6afc25a826` — page 2, section `PREAMBLE`**

```text
Whereas by virtue of Bennett University Statutes, the Vice Chancellor has been vested with all the

powers relating to discipline and disciplinary action in relation to students and now in pursuance

of the same the Vice Chancellor has approved the following rules of discipline and proper conduct

among the students of the University.
```

**Why it appears relevant:** Verified on page 2: the Vice Chancellor is vested with the relevant powers.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q005: Do these discipline rules cover part-time students and students admitted before the rules were notified?

- **Category:** `conduct_responsibilities`
- **Current relevant chunk IDs:** `de043ef96a8ae1f6`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 2: the rules apply to all students, including part-time students, before or after commencement.

#### Labelled source evidence

**Chunk `de043ef96a8ae1f6` — page 2, section `2. APPLICATION OF RULES`**

```text
1. These rules are not meant to deny the democratic rights of the students to dissent/air their

grievances/protest in a peaceful manner.

2. Peaceful sit-ins/dharanas at a designated place with prior intimation to the university

administration will not invite any punishment under these rules.

3. These Rules shall apply to all students of the University (including parttime students)

whether admitted prior to the commencement of these Rules or after the commencement of

these Rules.

4. Any breach of discipline and conduct committed by a student inside or outside the University

Campus shall fall under the purview of these Rules.

3. Code of Conduct: The Code of Conduct for students shall include:

i.

Observance of good conduct and orderly behavior within or outside the campus.

ii.

Emulating healthy traditions of the University and developing as responsible students at

the University.

iii.
```

**Why it appears relevant:** Verified on page 2: the rules apply to all students, including part-time students, before or after commencement.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q006: What kinds of behaviour are listed as Category I disciplinary misconduct?

- **Category:** `prohibited_activities`
- **Current relevant chunk IDs:** `067e151abf58a54b`, `cd21ed39ea433e92`, `b9d4a0253e0c7079`
- **Review status:** `REVIEWED — LABELS UNCHANGED; APPROVAL PENDING`
- **Current notes:** Verified on page 6: violence, coercion, privacy disturbance, and sexual-harassment examples.
- **Review note:** The complete Category I evidence in the processed corpus is on page 6. It is split across `067e151abf58a54b` (items 1 and 2, section metadata `CATEGORYI`), `cd21ed39ea433e92` (continuation of item 3, metadata `3. Sexual`), and `b9d4a0253e0c7079` (remainder of item 3 and item 4, metadata `Unwelcome`). The first Category II chunk is `4500b5e1df5458ab` and must not be treated as Category I evidence. A scan of the remaining processed corpus found no further Category I misconduct items.

#### Labelled source evidence

**Chunk `067e151abf58a54b` — page 6, section `CATEGORYI`**

```text
1. All acts of violence and all forms of coercion which disrupt the normal academic and

administrative functioning of the University and/or any act which encourages, abets or

leads to disorder and violence on campus.

2. Any form of coercion, intimidation or disturbance of right to privacy of the residents of

the campus.
```

**Why it appears relevant:** Verified on page 6: violence, coercion, privacy disturbance, and sexual-harassment examples.

**Chunk `cd21ed39ea433e92` — page 6, section `3. Sexual`**

```text
harassment

of

any

kind

which

shall

also

include:
```

**Why it appears relevant:** Verified on page 6: violence, coercion, privacy disturbance, and sexual-harassment examples.

**Chunk `b9d4a0253e0c7079` — page 6, section `Unwelcome`**

```text
sexual

proposition/advancements, sexually graphic comments of a body, unwelcome touching, patting,

pinching or leering of parts of the body or persistent offensive or unwelcome sexual jokes

and/or comments.

4. Arousing communal, caste or regional feeling or creating disharmony among students.
```

**Why it appears relevant:** Verified on page 6: violence, coercion, privacy disturbance, and sexual-harassment examples.

**Potentially missing or questionable evidence:** Potentially incomplete: Category I continues in chunks `4500b5e1df5458ab` and `8b899f2ff08fe95d`, which list additional Category I acts. Confirm whether the question requires the complete category list or representative examples.

---

### M41-Q007: Is cyberbullying treated as a disciplinary violation?

- **Category:** `prohibited_activities`
- **Current relevant chunk IDs:** `ff10accb8ee6929c`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 7: bullying in any form, including cyberbullying, is listed.

#### Labelled source evidence

**Chunk `ff10accb8ee6929c` — page 7, section `22. Possession, use, or distribution of drugs or psychotropic substances`**

```text
23. Bullying in any form whatsoever. Including cyber bullying

24. Engaging in discrimination of any sort against other students, the University employees, including

the faculty members, or employees of outsourced contractors working on the Campus, including

Sodexo staff, based on race, religion, gender, ethnicity, language, sexual orientation etc.

25. Abetting possession, use, or distribution of prohibited substance by other students through any

means, including financing.
```

**Why it appears relevant:** Verified on page 7: bullying in any form, including cyberbullying, is listed.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q008: What does the document say about possessing or distributing drugs or psychotropic substances?

- **Category:** `prohibited_activities`
- **Current relevant chunk IDs:** `ff10accb8ee6929c`, `d75de57ebb19414a`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Human approval remains pending. `ff10accb8ee6929c` is retained for its item 25 text about abetting another student's possession, use, or distribution. `d75de57ebb19414a` is retained as penalty evidence for statutory-offence table row 1 on printed page 20.

#### Labelled source evidence

**Chunk `ff10accb8ee6929c` — page 7, section `22. Possession, use, or distribution of drugs or psychotropic substances`**

```text
23. Bullying in any form whatsoever. Including cyber bullying

24. Engaging in discrimination of any sort against other students, the University employees, including

the faculty members, or employees of outsourced contractors working on the Campus, including

Sodexo staff, based on race, religion, gender, ethnicity, language, sexual orientation etc.

25. Abetting possession, use, or distribution of prohibited substance by other students through any

means, including financing.
```

**Why it appears relevant:** The text directly supports item 25: abetting another student's possession, use, or distribution of prohibited substance. The section metadata names item 22, but item 22's wording is absent from this chunk text; this chunk must not be treated as direct textual evidence for item 22.

**Chunk `d75de57ebb19414a` — page 20, section `Possession, use, or`**

```text
distribution of prohibited

substances or

psychotropic substances

•Expulsion from the University; and

•Intimation to Gautam Budh Nagar District Police for

appropriate action

2
```

**Why it appears relevant:** This is the penalty-table evidence for row 1 on printed page 20: expulsion from the University and intimation to Gautam Budh Nagar District Police.

#### Source-versus-corpus discrepancy

The original PDF contains the following page 7 item 22 wording:

```text
Possession, use, or distribution of drugs or psychotropic substances
```

That wording is missing from the text of `ff10accb8ee6929c`; only the item-22 heading survives in its section metadata. This is an ingestion/extraction defect, not evidence that the current chunk text contains item 22.

#### Candidate evidence pending approval

**Chunk `8b899f2ff08fe95d` — page 6, section `CATEGORYII`**

```text
8. Unauthorized occupation of the hostel room or unauthorized acquisition and use of university

furniture in one’s hostel room or elsewhere.

9. Indulging in acts of gambling in the University premises.

10. Consuming or possessing dangerous drugs or other intoxicants in the University premises.
```

**Candidate assessment:** This directly supports consuming or possessing dangerous drugs or other intoxicants in University premises. It does not establish distribution and does not specifically mention psychotropic substances.

**Chunk `d8fdccb230b145e7` — page 7, section `26. Indulging in any form of gambling/betting`**

```text
27. Parking of private cars on the Campus, or right outside the Campus

28. Abetting possession, use, or distribution of any kind of arms / ammunitions / weapons by

students through any means.

29. Cooking food in hostel rooms (Use of hot plates, electric cooker etc.)

30. Keeping pet/s or stray dogs; taking them inside the Hostel premises or academic block

31. Possession, me or distribution at prohibited substance/other similar products, infusing OCB

paper, chillum pipes and hookah (used for substance and other prohibited items on the Campus

32. Possession, use, or distribution of liquor/other intoxicants on the Campus OR A student found

in an inebriated condition on the Campus due to consumption of alcohol/other intoxicants.
```

**Candidate assessment:** Item 31 is relevant to possession/distribution of prohibited substances. The original PDF itself contains the malformed wording `me` and `at`; it must not be silently corrected or interpreted. Item 32 separately concerns liquor and other intoxicants.

**Potentially missing or questionable evidence:** The exact item 22 conduct text is missing from the processed chunk text and requires source-PDF verification before approval. `ff10accb8ee6929c` should remain a qualified item-25/metadata candidate, `d75de57ebb19414a` is penalty evidence, and `8b899f2ff08fe95d` plus `d8fdccb230b145e7` are additional candidates pending human approval.

---

### M41-Q009: Is gambling or betting prohibited on university premises?

- **Category:** `prohibited_activities`
- **Current relevant chunk IDs:** `d8fdccb230b145e7`, `52ddcdbb080cd9fa`, `de27a8ec20c10687`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on pages 7 and 22: gambling/betting is listed, including using university infrastructure to support it.

#### Labelled source evidence

**Chunk `d8fdccb230b145e7` — page 7, section `26. Indulging in any form of gambling/betting`**

```text
27. Parking of private cars on the Campus, or right outside the Campus

28. Abetting possession, use, or distribution of any kind of arms / ammunitions / weapons by

students through any means.

29. Cooking food in hostel rooms (Use of hot plates, electric cooker etc.)

30. Keeping pet/s or stray dogs; taking them inside the Hostel premises or academic block

31. Possession, me or distribution at prohibited substance/other similar products, infusing OCB

paper, chillum pipes and hookah (used for substance and other prohibited items on the Campus

32. Possession, use, or distribution of liquor/other intoxicants on the Campus OR A student found

in an inebriated condition on the Campus due to consumption of alcohol/other intoxicants.
```

**Why it appears relevant:** Verified on pages 7 and 22: gambling/betting is listed, including using university infrastructure to support it.

**Chunk `52ddcdbb080cd9fa` — page 22, section `Police for appropriate action`**

```text
9

a. Indulging in any form

of gambling/betting
```

**Why it appears relevant:** Verified on pages 7 and 22: gambling/betting is listed, including using university infrastructure to support it.

**Chunk `de27a8ec20c10687` — page 22, section `OR`**

```text
b. Using the University

infrastructure to provide

any assistance/ support to

any form of

gambling/betting

Undertaking by the student to the Proctorial Committee; and

•Written warning, and counselling;

or

•Suspension for 2 weeks, calling parents for a meeting with

the Members of the Proctorial Committee, and undertaking by

the parents to the Proctorial Committee;

or

•Suspension for up to one-semester and/or withholding of

Scholarship/ studentship for one year; and/or withholding of

Internship/ placement and other privileges;

or

•Suspension for up to one year, or expulsion from the
```

**Why it appears relevant:** Verified on pages 7 and 22: gambling/betting is listed, including using university infrastructure to support it.

**Potentially missing or questionable evidence:** Questionable: `d8fdccb230b145e7` lists nearby offences but does not mention gambling. `8b899f2ff08fe95d` directly mentions gambling and may be a missing or better label.

---

### M41-Q010: Can a student accommodate an unauthorized guest in a hall of residence?

- **Category:** `prohibited_activities`
- **Current relevant chunk IDs:** `611b52029bcb3803`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 7: accommodating unauthorized guests or other persons in halls is listed.

#### Labelled source evidence

**Chunk `611b52029bcb3803` — page 7, section `Page 7 of 23`**

```text
11. Damaging or defacing, in any form, or theft of any property of the University or the property of

any member of the University Community.

12. Not disclosing one’s identity when asked to do so by a faculty member or employee of the

University who is authorized to ask for such identity.

13. Improper behavior while on an official university tour or excursion.

14. Coercing the medical staff to render medical assistance to persons not entitled for the same

or any other disorderly behavior in the Wellness Centre.

15. Blockade or forceful prevention of any normal movement of traffic, violation of security, safety

rules notified by the University.

16. Any other offence under the law of land.

17. Ragging in any form.

18. Accommodating unauthorized guests or other persons in the halls of residence.

19. Engaging in any attempt at wrongful confinement of any member of the faculty, staff, student

or anyone camping inside the campus.

20. Any intimidation or insulting behavior towards a student, staff or faculty or any other person.

21. Any other act which may be considered by the Vice Chancellor or any other competent authority
```

**Why it appears relevant:** Verified on page 7: accommodating unauthorized guests or other persons in halls is listed.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q011: Is cooking with a hot plate or electric cooker in a hostel room allowed?

- **Category:** `prohibited_activities`
- **Current relevant chunk IDs:** `d8fdccb230b145e7`, `1bd03e260f92b3d0`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on pages 7 and 9: cooking in hostel rooms and the associated equipment rule are covered.

#### Labelled source evidence

**Chunk `d8fdccb230b145e7` — page 7, section `26. Indulging in any form of gambling/betting`**

```text
27. Parking of private cars on the Campus, or right outside the Campus

28. Abetting possession, use, or distribution of any kind of arms / ammunitions / weapons by

students through any means.

29. Cooking food in hostel rooms (Use of hot plates, electric cooker etc.)

30. Keeping pet/s or stray dogs; taking them inside the Hostel premises or academic block

31. Possession, me or distribution at prohibited substance/other similar products, infusing OCB

paper, chillum pipes and hookah (used for substance and other prohibited items on the Campus

32. Possession, use, or distribution of liquor/other intoxicants on the Campus OR A student found

in an inebriated condition on the Campus due to consumption of alcohol/other intoxicants.
```

**Why it appears relevant:** Verified on pages 7 and 9: cooking in hostel rooms and the associated equipment rule are covered.

**Chunk `1bd03e260f92b3d0` — page 9, section `Cooking food in`**

```text
hostel rooms &
```

**Why it appears relevant:** Verified on pages 7 and 9: cooking in hostel rooms and the associated equipment rule are covered.

**Potentially missing or questionable evidence:** Potentially incomplete: `1bd03e260f92b3d0` is only a continuation fragment. Confirm whether the question asks only whether cooking is prohibited or also requires the equipment exceptions/penalties in the page 9 chunks.

---

### M41-Q012: What can happen if a student leaves campus without permission or a gate pass?

- **Category:** `prohibited_activities`
- **Current relevant chunk IDs:** `7669e7dae47cf2b3`, `b6786e460d8f24f9`, `4b1d6525b819fe8d`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on pages 8 and 14: unauthorized departure is prohibited and penalties include warnings, fines, blocked gate passes, and possible expulsion from hostel.

#### Labelled source evidence

**Chunk `7669e7dae47cf2b3` — page 8, section `40. Unauthorized use/change of room`**

```text
41. Unauthorized departure from the Campus without prior permission or issue of ‘gate’ pass

42. Unauthorized entry into the terrace of the Academic Block, student housing blocks, faculty

housing, or any other area that is out of bounds for the students.
```

**Why it appears relevant:** Verified on pages 8 and 14: unauthorized departure is prohibited and penalties include warnings, fines, blocked gate passes, and possible expulsion from hostel.

**Chunk `b6786e460d8f24f9` — page 14, section `Page 14 of 23`**

```text
permission or

issue of ‘gate’

pass
```

**Why it appears relevant:** Verified on pages 8 and 14: unauthorized departure is prohibited and penalties include warnings, fines, blocked gate passes, and possible expulsion from hostel.

**Chunk `4b1d6525b819fe8d` — page 14, section `Committeeand`**

```text
undertaking by

parents to

proctorial

Committee. Fine

of Rupees

10000/- with

blocking of gate

passes for entire

semester.

studentship/Inter

nship/ placement

and other

privileges for one

year. Expulsion

from the Hostel
```

**Why it appears relevant:** Verified on pages 8 and 14: unauthorized departure is prohibited and penalties include warnings, fines, blocked gate passes, and possible expulsion from hostel.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q013: What happens if a student refuses a bag or luggage inspection?

- **Category:** `prohibited_activities`
- **Current relevant chunk IDs:** `3a0f8860a52bc4a2`, `55e8087c88228ea2`, `535c148766e9b21a`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on pages 8 and 11: refusal or resistance to checking is listed with a penalty table.

#### Labelled source evidence

**Chunk `3a0f8860a52bc4a2` — page 8, section `Page 8 of 23`**

```text
34. Refusal or resistance to checking of bags, wallet, luggage & eatable Items ordered from outside at

the Main Gate of the University or within U-Hall

35. Inducing workers to supply prohibited materials (tobacco/ alcohol, drugs, etc.)

36. Indecent exposure, obscene/lecherous conduct, either in a physical space or online
```

**Why it appears relevant:** Verified on pages 8 and 11: refusal or resistance to checking is listed with a penalty table.

**Chunk `55e8087c88228ea2` — page 11, section `Refusal or`**

```text
resistance to

checking of bags,

wallet, luggage &

eatable Items

ordered from

outside at the
```

**Why it appears relevant:** Verified on pages 8 and 11: refusal or resistance to checking is listed with a penalty table.

**Chunk `535c148766e9b21a` — page 11, section `University or`**

```text
Hostel blocks.
```

**Why it appears relevant:** Verified on pages 8 and 11: refusal or resistance to checking is listed with a penalty table.

**Potentially missing or questionable evidence:** Potentially incomplete: the current page 11 labels are continuation fragments and do not contain the full penalty table. Review adjacent page 11 chunks such as `4c30bc1f4cb9602e`.

---

### M41-Q014: Is lending a university identity card or access code to someone else a violation?

- **Category:** `prohibited_activities`
- **Current relevant chunk IDs:** `4cc62505faa68f61`, `4fdfafc18b3d0fed`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 23: lending identity cards, codes, or university-app access is addressed.

#### Labelled source evidence

**Chunk `4cc62505faa68f61` — page 23, section `Page 23 of 23`**

```text
10

a. Lending of Identity
```

**Why it appears relevant:** Verified on page 23: lending identity cards, codes, or university-app access is addressed.

**Chunk `4fdfafc18b3d0fed` — page 23, section `Card/ codes /access`**

```text
univerty Apps for entry

into campus/hostel/

dining hall for meals Or

taking a dayscholar to an

area where they are not

permitted, without a

written authorization

from the University

authorities
```

**Why it appears relevant:** Verified on page 23: lending identity cards, codes, or university-app access is addressed.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q015: What kinds of discrimination are prohibited by the rules?

- **Category:** `prohibited_activities`
- **Current relevant chunk IDs:** `ff10accb8ee6929c`, `a31ed4f0b92139ff`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on pages 7 and 22: discrimination based on listed personal characteristics is prohibited.

#### Labelled source evidence

**Chunk `ff10accb8ee6929c` — page 7, section `22. Possession, use, or distribution of drugs or psychotropic substances`**

```text
23. Bullying in any form whatsoever. Including cyber bullying

24. Engaging in discrimination of any sort against other students, the University employees, including

the faculty members, or employees of outsourced contractors working on the Campus, including

Sodexo staff, based on race, religion, gender, ethnicity, language, sexual orientation etc.

25. Abetting possession, use, or distribution of prohibited substance by other students through any

means, including financing.
```

**Why it appears relevant:** Verified on pages 7 and 22: discrimination based on listed personal characteristics is prohibited.

**Chunk `a31ed4f0b92139ff` — page 22, section `Engaging in`**

```text
discrimination of any sort

against other students,

the University employees,

including the faculty

members, or employees of

outsourced contractors

working on the Campus,

including any 3rd party

vendor’s staff, based on

race, religion, gender,

ethnicity, language, etc.

Undertaking by the student to the Proctorial Committee; and

•Written warning, and counselling;

or

•Suspension for 2 weeks, calling parents for a meeting with

the Members of the Proctorial Committee, and undertaking by

the parents to the Proctorial Committee;

or

•Suspension for up to one-semester and/or withholding of

Scholarship/ studentship for one year; and/or withholding of

Internship/ placement and other privileges;

or

•Suspension for up to one year, or expulsion from the
```

**Why it appears relevant:** Verified on pages 7 and 22: discrimination based on listed personal characteristics is prohibited.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q016: What happens after the university receives a misconduct complaint?

- **Category:** `investigation_procedure`
- **Current relevant chunk IDs:** `8995f95b4d376550`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 3: the complaint is scrutinized for Proctorial Committee jurisdiction.

#### Labelled source evidence

**Chunk `8995f95b4d376550` — page 3, section `Page 3 of 23`**

```text
5. Procedures for Enquiry and Punishment:

 After receipt of a complaint (directly to the Chief Proctor or forwarded by the Vice Chancel

lor/Pro Vice-Chancellor) it is scrutinized by the Proctorial Committee to ascertain if it

pertains to the jurisdiction of Proctorial enquiry.

 Three members of the Proctorial committee will constitute the quorum for such enquiry.

The Proctorial Committee is an internal enquiry of bennett University and hence, no

other person except the Committee members is allowed to present during hearings. The

accused or complainants are not allowed to berepresented by a third party.

 Similarly, he/she cannot have an observer during the process of enquiry.

After it is ascertained that an enquiry is required, following procedure/norm is generally followed:

1. The complainant is called for a hearing and his/her deposition is recorded.

2. The accused person(s) is/are called for recording his/her statement.

3. Witnesses mentioned by both parties are listed and they are called for recording their depositions.

4. Any evidence, from security staff/University staff or other persons, who were present there and
```

**Why it appears relevant:** Verified on page 3: the complaint is scrutinized for Proctorial Committee jurisdiction.

**Potentially missing or questionable evidence:** Potentially incomplete: `8995f95b4d376550` covers complaint receipt and initial steps, but the wording “what happens after” may require `0cdb342f55dd0425` and later procedural chunks.

---

### M41-Q017: Whose statements and evidence are considered during a disciplinary enquiry?

- **Category:** `investigation_procedure`
- **Current relevant chunk IDs:** `8995f95b4d376550`, `0cdb342f55dd0425`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 3: complainant, accused, witnesses, staff evidence, and material evidence are described.

#### Labelled source evidence

**Chunk `8995f95b4d376550` — page 3, section `Page 3 of 23`**

```text
5. Procedures for Enquiry and Punishment:

 After receipt of a complaint (directly to the Chief Proctor or forwarded by the Vice Chancel

lor/Pro Vice-Chancellor) it is scrutinized by the Proctorial Committee to ascertain if it

pertains to the jurisdiction of Proctorial enquiry.

 Three members of the Proctorial committee will constitute the quorum for such enquiry.

The Proctorial Committee is an internal enquiry of bennett University and hence, no

other person except the Committee members is allowed to present during hearings. The

accused or complainants are not allowed to berepresented by a third party.

 Similarly, he/she cannot have an observer during the process of enquiry.

After it is ascertained that an enquiry is required, following procedure/norm is generally followed:

1. The complainant is called for a hearing and his/her deposition is recorded.

2. The accused person(s) is/are called for recording his/her statement.

3. Witnesses mentioned by both parties are listed and they are called for recording their depositions.

4. Any evidence, from security staff/University staff or other persons, who were present there and
```

**Why it appears relevant:** Verified on page 3: complainant, accused, witnesses, staff evidence, and material evidence are described.

**Chunk `0cdb342f55dd0425` — page 3, section `Page 3 of 23`**

```text
had witnessed the incident, are called and their statements recorded.

5. A cross examination of the accused and the complainant is conducted.

6. If there is any material evidence, like audio/video tapes/paper documents etc. is available,

the same is examined. The veracity is established from the person who submits these.

7. Finally, a comprehensive report is prepared where specific charges against the accused is framed

and a show cause notice is issued.

8. The defense given by the accused persons in the show cause notice is studied and examined.

9. Finally, a report is prepared and as per the “Rules of discipline and proper code of conduct of the

University,” appropriate disciplinary action is recommended.
```

**Why it appears relevant:** Verified on page 3: complainant, accused, witnesses, staff evidence, and material evidence are described.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q018: How does the committee handle audio, video, or paper evidence?

- **Category:** `investigation_procedure`
- **Current relevant chunk IDs:** `0cdb342f55dd0425`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 3: material evidence is examined and its veracity is established with the submitter.

#### Labelled source evidence

**Chunk `0cdb342f55dd0425` — page 3, section `Page 3 of 23`**

```text
had witnessed the incident, are called and their statements recorded.

5. A cross examination of the accused and the complainant is conducted.

6. If there is any material evidence, like audio/video tapes/paper documents etc. is available,

the same is examined. The veracity is established from the person who submits these.

7. Finally, a comprehensive report is prepared where specific charges against the accused is framed

and a show cause notice is issued.

8. The defense given by the accused persons in the show cause notice is studied and examined.

9. Finally, a report is prepared and as per the “Rules of discipline and proper code of conduct of the

University,” appropriate disciplinary action is recommended.
```

**Why it appears relevant:** Verified on page 3: material evidence is examined and its veracity is established with the submitter.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q019: Why is a show-cause notice issued in the enquiry process?

- **Category:** `investigation_procedure`
- **Current relevant chunk IDs:** `0cdb342f55dd0425`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 3: charges are framed, a show-cause notice is issued, and the defence is examined.

#### Labelled source evidence

**Chunk `0cdb342f55dd0425` — page 3, section `Page 3 of 23`**

```text
had witnessed the incident, are called and their statements recorded.

5. A cross examination of the accused and the complainant is conducted.

6. If there is any material evidence, like audio/video tapes/paper documents etc. is available,

the same is examined. The veracity is established from the person who submits these.

7. Finally, a comprehensive report is prepared where specific charges against the accused is framed

and a show cause notice is issued.

8. The defense given by the accused persons in the show cause notice is studied and examined.

9. Finally, a report is prepared and as per the “Rules of discipline and proper code of conduct of the

University,” appropriate disciplinary action is recommended.
```

**Why it appears relevant:** Verified on page 3: charges are framed, a show-cause notice is issued, and the defence is examined.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q020: What can the Proctorial Committee do if the accused student does not appear?

- **Category:** `investigation_procedure`
- **Current relevant chunk IDs:** `047e458c9fdc7f71`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 5: the committee may draw a conclusion ex parte and submit the documents.

#### Labelled source evidence

**Chunk `047e458c9fdc7f71` — page 5, section `Page 5 of 23`**

```text
x.

During the period of inquiry, the University Proctorial Committee will be empowered to

suspend the student if in its judgment it is in the larger interest of the student community, or

the evidence / safety of witnesses is likely to get affected. (Reasons for suspension will be

stated in the Proctorial Committee proceedings.) Notwithstanding completion of the

proceedings, such suspension will be revoked as soon as feasible. The period of suspension

undergone will be considered while awarding the penalty.

xi.

The Proctorial Committee is to keep a record of the proceedings and compile a report

containing all facts and evidence that has been placed before it. Such a report along with the

recommendations and punishment to be imposed is to be given to the Registrar, who would

forward the same to the Vice-Chancellor for further action (as the case may be). If the guilty

student fails to appear, the Proctorial Committee will have the right to draw its conclusion

ex parte and submit the aforesaid documents to the Registrar.

xii.

The final decision, in the form of penalty letters, shall be communicated to the convicted
```

**Why it appears relevant:** Verified on page 5: the committee may draw a conclusion ex parte and submit the documents.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q021: What deadlines are stated for convening a Proctorial Committee and submitting recommendations?

- **Category:** `investigation_procedure`
- **Current relevant chunk IDs:** `df3dfc8b2bc5d039`, `e1d1f1cadd1a923a`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 4: notice within 3 days, school meeting within 5 days, and recommendations within the next 7 days.

#### Labelled source evidence

**Chunk `df3dfc8b2bc5d039` — page 4, section `Page 4 of 23`**

```text
other Committees formed under the rules. (However, a student making a complaint to a

member of the Proctorial Committee / Internal Complaints Committee (ICC) / ARC, etc. will

not debar such member from sitting as a member.)

vi.

All Pr proceedings will be put up to the VC through Chief Proctor, after technical scrutiny by

the Deputy Proctor. Where necessary, vetting from the legal department should be done in

cases of award of major penalty by the Central Deputy Proctor or Dean Student Affairs.

vii.

The Deputy Proctor will also keep all the Proctorial Committee proceedings / documents in

own custody as confidential documents.

viii.

A notice for convening the Proctorial Committee indicating date, time and the venue shall be

issued (within 3 days of the offence) by the Dean Student Affairs / Deputy Proctor in

consultation with the Chairman of the Proctorial Committee (Chief Proctor) and the guilty

students shall be given an opportunity to appear before the committee for cross examination

and interrogation.

ix.

The School Proctorial Committee shall hold its meeting at the latest within 5 days of the
```

**Why it appears relevant:** Verified on page 4: notice within 3 days, school meeting within 5 days, and recommendations within the next 7 days.

**Chunk `e1d1f1cadd1a923a` — page 4, section `Page 4 of 23`**

```text
offence and submit recommendations within the next 7 days to the University proctorial

Committee. Record of Proctorial Committee meetings and adjournments also mentioning the

reasons shall be kept by the Member Secretary of the Proctorial Committee (both at the

school and the University level).
```

**Why it appears relevant:** Verified on page 4: notice within 3 days, school meeting within 5 days, and recommendations within the next 7 days.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q022: How does the Deputy Proctor decide whether a case is dismissed or escalated?

- **Category:** `committees_and_powers`
- **Current relevant chunk IDs:** `94dc298b1e4ee1aa`, `1c5dc37875e96455`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on pages 3 and 4: after preliminary enquiry and assessing seriousness, a case may receive a minor penalty or escalate.

#### Labelled source evidence

**Chunk `94dc298b1e4ee1aa` — page 3, section `10. Final report and recommendations are submitted to the ProVice-Chancellor`**

```text
for approval &final decision.Consequently, the award of punishment is conveyed to the student.

11. The aggrieved student has the right to appeal to Vice Chancellor gainst the punishment and Vice

Chancellor is the empowered authority to deal with appeals.

The above mentioned norms and procedures are generally followed. However, the Proctorial Committee

at its discretion can add additional norms or delete existing ones separately depending on the nature and

need of the enquiry.

i.

All cases of indiscipline and misbehavior shall be referred immediately to the Deputy Proctor

directly or through the School Dean/ Dean Student Affairs (DSA)/Registrar. After a

preliminary enquiry and assessing the nature and seriousness of the act, the Deputy Proctor

shall: either recommend to the DSA/ Registrar (Ex-officio Chairman of BU Proctorial

Committee),summary dismissal of the case with minor penalty as specified for general /
```

**Why it appears relevant:** Verified on pages 3 and 4: after preliminary enquiry and assessing seriousness, a case may receive a minor penalty or escalate.

**Chunk `1c5dc37875e96455` — page 4, section `Page 4 of 23`**

```text
classroom misconduct or escalate to University Proctorial Committee and place the facts and

evidence gathered before it.

ii.

Registrar to issue the Promulgation Orders in all cases.

iii.

The University Proctorial Committee Chairperson will inform Vice Chancellor /Pro Vice

Chancellor in case of all major incidents and proposed nature of P being convened and act as

per his directions.

iv.

As a guideline, reported incidents of major / serious offences and which may have occurred

off- campus or where students or persons of other schools, departments or non-BU persons

may be involved or become witness; will generally be dealt by the University Proctorial

Committee. However, the availability of Proctors may also be kept in mind and on no account

should the convening of a Proctorial Committee be delayed.

v.

While deciding on the composition of the Proctorial Committee to deal with a case it shall be

ensured that the person who may have initially investigated the case (like hostel warden or

member of anti-ragging squad) is not called upon as a member of the said committee. This

provision shall also apply to the Anti Ragging Committee (ARC) Disciplinary Panel and to any
```

**Why it appears relevant:** Verified on pages 3 and 4: after preliminary enquiry and assessing seriousness, a case may receive a minor penalty or escalate.

**Potentially missing or questionable evidence:** Potentially weak label: `94dc298b1e4ee1aa` contains the relevant Deputy Proctor screening text later in the chunk but begins with final-report/appeal context. Confirm whether it should remain relevant.

---

### M41-Q023: When will a serious or off-campus incident generally be handled by the University Proctorial Committee?

- **Category:** `committees_and_powers`
- **Current relevant chunk IDs:** `1c5dc37875e96455`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 4: major or serious incidents, including off-campus matters or external witnesses, generally go to the University Committee.

#### Labelled source evidence

**Chunk `1c5dc37875e96455` — page 4, section `Page 4 of 23`**

```text
classroom misconduct or escalate to University Proctorial Committee and place the facts and

evidence gathered before it.

ii.

Registrar to issue the Promulgation Orders in all cases.

iii.

The University Proctorial Committee Chairperson will inform Vice Chancellor /Pro Vice

Chancellor in case of all major incidents and proposed nature of P being convened and act as

per his directions.

iv.

As a guideline, reported incidents of major / serious offences and which may have occurred

off- campus or where students or persons of other schools, departments or non-BU persons

may be involved or become witness; will generally be dealt by the University Proctorial

Committee. However, the availability of Proctors may also be kept in mind and on no account

should the convening of a Proctorial Committee be delayed.

v.

While deciding on the composition of the Proctorial Committee to deal with a case it shall be

ensured that the person who may have initially investigated the case (like hostel warden or

member of anti-ragging squad) is not called upon as a member of the said committee. This

provision shall also apply to the Anti Ragging Committee (ARC) Disciplinary Panel and to any
```

**Why it appears relevant:** Verified on page 4: major or serious incidents, including off-campus matters or external witnesses, generally go to the University Committee.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q024: Can the person who first investigated a case sit on the committee deciding it?

- **Category:** `committees_and_powers`
- **Current relevant chunk IDs:** `1c5dc37875e96455`, `df3dfc8b2bc5d039`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 4: the initial investigator should not be a committee member, subject to the stated complaint-member exception.

#### Labelled source evidence

**Chunk `1c5dc37875e96455` — page 4, section `Page 4 of 23`**

```text
classroom misconduct or escalate to University Proctorial Committee and place the facts and

evidence gathered before it.

ii.

Registrar to issue the Promulgation Orders in all cases.

iii.

The University Proctorial Committee Chairperson will inform Vice Chancellor /Pro Vice

Chancellor in case of all major incidents and proposed nature of P being convened and act as

per his directions.

iv.

As a guideline, reported incidents of major / serious offences and which may have occurred

off- campus or where students or persons of other schools, departments or non-BU persons

may be involved or become witness; will generally be dealt by the University Proctorial

Committee. However, the availability of Proctors may also be kept in mind and on no account

should the convening of a Proctorial Committee be delayed.

v.

While deciding on the composition of the Proctorial Committee to deal with a case it shall be

ensured that the person who may have initially investigated the case (like hostel warden or

member of anti-ragging squad) is not called upon as a member of the said committee. This

provision shall also apply to the Anti Ragging Committee (ARC) Disciplinary Panel and to any
```

**Why it appears relevant:** Verified on page 4: the initial investigator should not be a committee member, subject to the stated complaint-member exception.

**Chunk `df3dfc8b2bc5d039` — page 4, section `Page 4 of 23`**

```text
other Committees formed under the rules. (However, a student making a complaint to a

member of the Proctorial Committee / Internal Complaints Committee (ICC) / ARC, etc. will

not debar such member from sitting as a member.)

vi.

All Pr proceedings will be put up to the VC through Chief Proctor, after technical scrutiny by

the Deputy Proctor. Where necessary, vetting from the legal department should be done in

cases of award of major penalty by the Central Deputy Proctor or Dean Student Affairs.

vii.

The Deputy Proctor will also keep all the Proctorial Committee proceedings / documents in

own custody as confidential documents.

viii.

A notice for convening the Proctorial Committee indicating date, time and the venue shall be

issued (within 3 days of the offence) by the Dean Student Affairs / Deputy Proctor in

consultation with the Chairman of the Proctorial Committee (Chief Proctor) and the guilty

students shall be given an opportunity to appear before the committee for cross examination

and interrogation.

ix.

The School Proctorial Committee shall hold its meeting at the latest within 5 days of the
```

**Why it appears relevant:** Verified on page 4: the initial investigator should not be a committee member, subject to the stated complaint-member exception.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q025: Who keeps the Proctorial Committee proceedings and documents confidential?

- **Category:** `committees_and_powers`
- **Current relevant chunk IDs:** `df3dfc8b2bc5d039`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 4: the Deputy Proctor keeps the proceedings and documents as confidential documents.

#### Labelled source evidence

**Chunk `df3dfc8b2bc5d039` — page 4, section `Page 4 of 23`**

```text
other Committees formed under the rules. (However, a student making a complaint to a

member of the Proctorial Committee / Internal Complaints Committee (ICC) / ARC, etc. will

not debar such member from sitting as a member.)

vi.

All Pr proceedings will be put up to the VC through Chief Proctor, after technical scrutiny by

the Deputy Proctor. Where necessary, vetting from the legal department should be done in

cases of award of major penalty by the Central Deputy Proctor or Dean Student Affairs.

vii.

The Deputy Proctor will also keep all the Proctorial Committee proceedings / documents in

own custody as confidential documents.

viii.

A notice for convening the Proctorial Committee indicating date, time and the venue shall be

issued (within 3 days of the offence) by the Dean Student Affairs / Deputy Proctor in

consultation with the Chairman of the Proctorial Committee (Chief Proctor) and the guilty

students shall be given an opportunity to appear before the committee for cross examination

and interrogation.

ix.

The School Proctorial Committee shall hold its meeting at the latest within 5 days of the
```

**Why it appears relevant:** Verified on page 4: the Deputy Proctor keeps the proceedings and documents as confidential documents.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q026: What punishments are listed for Category I misconduct?

- **Category:** `punishments_penalties`
- **Current relevant chunk IDs:** `0320a43289fbdbe8`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 8: cancellation or withdrawal, rustication, out-of-bounds orders, and expulsion.

#### Labelled source evidence

**Chunk `0320a43289fbdbe8` — page 8, section `CATEGORY I`**

```text
1. Cancellation of admission or withdrawal of degree or denial of registration for a specified

period.

2. Rustication up to 2-4 semesters period and/or declaring any part or the entire University

Campus out of bounds.

3. Expulsion.
```

**Why it appears relevant:** Verified on page 8: cancellation or withdrawal, rustication, out-of-bounds orders, and expulsion.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q027: What punishments are listed for Category II misconduct?

- **Category:** `punishments_penalties`
- **Current relevant chunk IDs:** `8fce4c0b6a83c0fd`, `895bb5ab0b064e1c`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on pages 8 and 9: reprimand, fines, recovery, withdrawal of facilities, stoppage of academic processes, out-of-bounds orders, and rustication.

#### Labelled source evidence

**Chunk `8fce4c0b6a83c0fd` — page 8, section `CATEGORY II`**

```text
1. Admonition/Reprimand.

2. Fine up to Rs. 10,000/ 3. Recovery of any kind, such as scholarship/fellowship, any dues, cost of damages etc.

4. In case of damaging, defacing or theft of any property of the University or the property of any

member of the University Community, cost of damaged/defaced/stolen property plus a fine

up to a maximum amount of Rs 10,000/- (Rs Ten Thousand only) may be imposed upon the

persons(s) found guilty by the Proctorial Committee.

5. Withdrawal of any or all facilities available to a student as per University Rules (such as

Scholarship/Fellowship, hostel etc.)
```

**Why it appears relevant:** Verified on pages 8 and 9: reprimand, fines, recovery, withdrawal of facilities, stoppage of academic processes, out-of-bounds orders, and rustication.

**Chunk `895bb5ab0b064e1c` — page 9, section `Page 9 of 23`**

```text
6. Stoppage of any or all academic processes.

7. Declaring any Halls of Residences, premises, building or the entire University Campus out

of bounds to any student.

8. Rustication up to two semesters.
```

**Why it appears relevant:** Verified on pages 8 and 9: reprimand, fines, recovery, withdrawal of facilities, stoppage of academic processes, out-of-bounds orders, and rustication.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q028: What penalties can apply when university property is damaged or stolen?

- **Category:** `punishments_penalties`
- **Current relevant chunk IDs:** `8fce4c0b6a83c0fd`, `c69573124c7ca1be`, `1096dc30c910dca8`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on pages 8 and 11: recovery/fines, warnings, suspension, withholding privileges, or expulsion are described.

#### Labelled source evidence

**Chunk `8fce4c0b6a83c0fd` — page 8, section `CATEGORY II`**

```text
1. Admonition/Reprimand.

2. Fine up to Rs. 10,000/ 3. Recovery of any kind, such as scholarship/fellowship, any dues, cost of damages etc.

4. In case of damaging, defacing or theft of any property of the University or the property of any

member of the University Community, cost of damaged/defaced/stolen property plus a fine

up to a maximum amount of Rs 10,000/- (Rs Ten Thousand only) may be imposed upon the

persons(s) found guilty by the Proctorial Committee.

5. Withdrawal of any or all facilities available to a student as per University Rules (such as

Scholarship/Fellowship, hostel etc.)
```

**Why it appears relevant:** Verified on pages 8 and 11: recovery/fines, warnings, suspension, withholding privileges, or expulsion are described.

**Chunk `c69573124c7ca1be` — page 11, section `Damaging/steali`**

```text
ng University

property

including

provided by

third party

vendors working

inside campus
```

**Why it appears relevant:** Verified on pages 8 and 11: recovery/fines, warnings, suspension, withholding privileges, or expulsion are described.

**Chunk `1096dc30c910dca8` — page 11, section `Counselling & calling`**

```text
parents for a meeting

with the hostel

administration/concern

authority. Written

warning by hostel

administration/security

/Programme

coordinator to the

student and fine upto

five times the cost of

the property.
```

**Why it appears relevant:** Verified on pages 8 and 11: recovery/fines, warnings, suspension, withholding privileges, or expulsion are described.

**Potentially missing or questionable evidence:** Incorrect-looking label: `66f41fbf883ec7a2` is only the word “University.” and does not provide property-damage evidence. Review adjacent page 15/property-penalty chunks and consider removing it.

---

### M41-Q029: What sanctions are described for alcohol possession or being intoxicated on campus?

- **Category:** `punishments_penalties`
- **Current relevant chunk IDs:** `4d05133a12ccb25e`, `fbf867d031fbe036`, `759eccd49a9822da`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on pages 10 and 11: the prohibited conduct and escalating warning, fine, suspension, withholding, and expulsion outcomes are covered.

#### Labelled source evidence

**Chunk `4d05133a12ccb25e` — page 10, section `Expulsion from`**

```text
university.

5

a. Possession,

use, or

distribution of

liquor/other

intoxicants on

the Campus
```

**Why it appears relevant:** Verified on pages 10 and 11: the prohibited conduct and escalating warning, fine, suspension, withholding, and expulsion outcomes are covered.

**Chunk `fbf867d031fbe036` — page 10, section `OR`**

```text
b. A student

found in an

inebriated

condition on the
```

**Why it appears relevant:** Verified on pages 10 and 11: the prohibited conduct and escalating warning, fine, suspension, withholding, and expulsion outcomes are covered.

**Chunk `759eccd49a9822da` — page 10, section `Proctorial`**

```text
Committee.Couns

elling calling

parents for a

meeting with

members of

proctorial

Committee. Fine

of rupees 10000/ Undertaking by

student's parents

to Proctorial

Committee. Fine

of Rupees

20000/- and

suspension up to

one year without

academic

attendance.
```

**Why it appears relevant:** Verified on pages 10 and 11: the prohibited conduct and escalating warning, fine, suspension, withholding, and expulsion outcomes are covered.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q030: What penalties may follow physical violence or causing bodily injury?

- **Category:** `punishments_penalties`
- **Current relevant chunk IDs:** `9ee67371159ace93`, `0396efee68c45a18`, `66f41fbf883ec7a2`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on pages 15 and 21: warnings/counselling, suspension, withholding privileges, and expulsion are listed.

#### Labelled source evidence

**Chunk `9ee67371159ace93` — page 21, section `Page 21 of 23`**

```text
4

a. Engaging in physical

altercation/violence
```

**Why it appears relevant:** Verified on pages 15 and 21: warnings/counselling, suspension, withholding privileges, and expulsion are listed.

**Chunk `0396efee68c45a18` — page 21, section `Causing`**

```text
bodily

harm/injury

to

other

students, the University

employees, including the

faculty

members,

or

employees of outsourced

contractors working on

the Campus, including any

3rd party vendor’s staff

Undertaking by the student to the Proctorial Committee; and

•Written warning, and counselling; or

•Suspension for 2 weeks, calling parents for a meeting with

the Members of the Proctorial Committee, and undertaking

by the parents to the Proctorial Committee;

or

•Suspension for up to one-semester and/or withholding of

Scholarship/ studentship for one year; and/

or withholding of Internship/ placement and other

privileges; or

•Suspension for up to one year, or expulsion from the
```

**Why it appears relevant:** Verified on pages 15 and 21: warnings/counselling, suspension, withholding privileges, and expulsion are listed.

**Chunk `66f41fbf883ec7a2` — page 15, section `Or expulsion from`**

```text
University.
```

**Why it appears relevant:** Verified on pages 15 and 21: warnings/counselling, suspension, withholding privileges, and expulsion are listed.

**Potentially missing or questionable evidence:** Incorrect-looking label: `66f41fbf883ec7a2` is only the word “University.” and does not support physical-violence penalties. Review `09a8f3b9f3bb9c99` and following page 15 penalty chunks.

---

### M41-Q031: How soon and to whom must a student submit an appeal against a penalty?

- **Category:** `appeals_review`
- **Current relevant chunk IDs:** `74b85be0218069f0`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 5: the appeal is written to the Vice-Chancellor within 5 working days of service of the order.

#### Labelled source evidence

**Chunk `74b85be0218069f0` — page 5, section `Page 5 of 23`**

```text
student(s) and to their parents by the Deputy Proctors (for School Proctorial Committee ) /

Chief proctor (for University Proctorial Committee).

xiii.

The information about any disciplinary / other official matter will be shared on their official

mail ID as per records or by post / parent’s mail ID or / and postal address.

6. Appeal:

i.

A student having been awarded a penalty for any act(s) of indiscipline or misconduct shall have

the right to file an appeal (in writing) for review of the decision to the Vice-Chancellor within

5 working days of the service of the order.

ii.

The powers to review the major penalties imposed shall lie with the Vice-Chancellor. Powers

to review the minor penalties shall be with Chief Proctor / School Dean on one level above

principle.

iii.

The Vice-Chancellor may either maintain the earlier decision, moderate or escalate the penalty

awarded. In exceptional case, it may be referred back to the Proctorial Committee for review,

if any

new submissions have been made by the student in his appeal.

iv.

The decision of the Vice-Chancellor following the appeal will be final (as the case may be) and
```

**Why it appears relevant:** Verified on page 5: the appeal is written to the Vice-Chancellor within 5 working days of service of the order.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

### M41-Q032: Who reviews major and minor penalties, and what can the Vice-Chancellor decide?

- **Category:** `appeals_review`
- **Current relevant chunk IDs:** `74b85be0218069f0`
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Current notes:** Verified on page 5: review authority differs for major and minor penalties; the Vice-Chancellor may maintain, moderate, escalate, or refer back in exceptional cases.

#### Labelled source evidence

**Chunk `74b85be0218069f0` — page 5, section `Page 5 of 23`**

```text
student(s) and to their parents by the Deputy Proctors (for School Proctorial Committee ) /

Chief proctor (for University Proctorial Committee).

xiii.

The information about any disciplinary / other official matter will be shared on their official

mail ID as per records or by post / parent’s mail ID or / and postal address.

6. Appeal:

i.

A student having been awarded a penalty for any act(s) of indiscipline or misconduct shall have

the right to file an appeal (in writing) for review of the decision to the Vice-Chancellor within

5 working days of the service of the order.

ii.

The powers to review the major penalties imposed shall lie with the Vice-Chancellor. Powers

to review the minor penalties shall be with Chief Proctor / School Dean on one level above

principle.

iii.

The Vice-Chancellor may either maintain the earlier decision, moderate or escalate the penalty

awarded. In exceptional case, it may be referred back to the Proctorial Committee for review,

if any

new submissions have been made by the student in his appeal.

iv.

The decision of the Vice-Chancellor following the appeal will be final (as the case may be) and
```

**Why it appears relevant:** Verified on page 5: review authority differs for major and minor penalties; the Vice-Chancellor may maintain, moderate, escalate, or refer back in exceptional cases.

**Potentially missing or questionable evidence:** No specific omission was identified during the initial audit; independently confirm that the labelled text directly answers the question and that no adjacent continuation is required.

---

## Unsupported questions

These questions have no current relevant chunk IDs. The unsupported status is also pending human confirmation against the full ingested corpus. The scholarship PDF in `data/input/` is not part of the processed corpus.

### M41-Q033: What is the tuition fee deadline for this semester?

- **Category:** `unsupported`
- **Current relevant chunk IDs:** none
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Why currently unsupported:** The ingested discipline document contains no tuition-fee calendar or deadline. The scholarship PDF is not processed or embedded.
- **Human check:** Search the complete discipline corpus for direct evidence; do not treat keyword overlap, hostel references, scholarship withholding, or dining-hall access codes as an answer to the requested fact.

---

### M41-Q034: What attendance percentage must a student maintain to sit for examinations?

- **Category:** `unsupported`
- **Current relevant chunk IDs:** none
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Why currently unsupported:** No attendance requirement or examination eligibility rule is present in the ingested discipline document.
- **Human check:** Search the complete discipline corpus for direct evidence; do not treat keyword overlap, hostel references, scholarship withholding, or dining-hall access codes as an answer to the requested fact.

---

### M41-Q035: How do I apply for a Bennett University scholarship?

- **Category:** `unsupported`
- **Current relevant chunk IDs:** none
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Why currently unsupported:** A scholarship PDF exists under data/input but has not been ingested, so it cannot support an answer in this evaluation.
- **Human check:** Search the complete discipline corpus for direct evidence; do not treat keyword overlap, hostel references, scholarship withholding, or dining-hall access codes as an answer to the requested fact.

---

### M41-Q036: Where can I find the examination timetable for my programme?

- **Category:** `unsupported`
- **Current relevant chunk IDs:** none
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Why currently unsupported:** The current processed corpus contains no examination timetable or programme calendar.
- **Human check:** Search the complete discipline corpus for direct evidence; do not treat keyword overlap, hostel references, scholarship withholding, or dining-hall access codes as an answer to the requested fact.

---

### M41-Q037: How do I apply for a hostel room for next semester?

- **Category:** `unsupported`
- **Current relevant chunk IDs:** none
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Why currently unsupported:** The discipline document mentions hostel violations and penalties, not room-allocation procedures.
- **Human check:** Search the complete discipline corpus for direct evidence; do not treat keyword overlap, hostel references, scholarship withholding, or dining-hall access codes as an answer to the requested fact.

---

### M41-Q038: What is the library fine for returning a book late?

- **Category:** `unsupported`
- **Current relevant chunk IDs:** none
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Why currently unsupported:** The discipline document mentions unauthorized possession or damage of library material but gives no overdue-book fine.
- **Human check:** Search the complete discipline corpus for direct evidence; do not treat keyword overlap, hostel references, scholarship withholding, or dining-hall access codes as an answer to the requested fact.

---

### M41-Q039: How do I register for courses or change my class section?

- **Category:** `unsupported`
- **Current relevant chunk IDs:** none
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Why currently unsupported:** No course-registration or section-change procedure is present in the ingested corpus.
- **Human check:** Search the complete discipline corpus for direct evidence; do not treat keyword overlap, hostel references, scholarship withholding, or dining-hall access codes as an answer to the requested fact.

---

### M41-Q040: How much does a meal at the university dining hall cost?

- **Category:** `unsupported`
- **Current relevant chunk IDs:** none
- **Review status:** `PENDING_HUMAN_REVIEW`
- **Why currently unsupported:** The document references dining-hall access codes but contains no meal prices.
- **Human check:** Search the complete discipline corpus for direct evidence; do not treat keyword overlap, hostel references, scholarship withholding, or dining-hall access codes as an answer to the requested fact.

---

## Audit summary

- **Answerable labels appearing well-supported on initial inspection:** 23 questions. These still require confirmation because every review status remains pending.
- **Answerable labels requiring focused human judgment:** 9 questions: M41-Q006, M41-Q008, M41-Q009, M41-Q011, M41-Q013, M41-Q016, M41-Q022, M41-Q028, and M41-Q030.
- **Unsupported questions requiring human judgment:** 8 questions (M41-Q033 through M41-Q040).
- **Suspected missing or questionable evidence:** Category I continuation chunks for Q006; direct possession/gambling chunks for Q008–Q009; continuation/penalty chunks for Q011 and Q013; broader procedure chunks for Q016; a partial screening chunk for Q022; and the fragment `66f41fbf883ec7a2` for Q028 and Q030.
- **Suspected incorrectly labelled chunks:** `d8fdccb230b145e7` for Q009 and `66f41fbf883ec7a2` for Q028/Q030 appear not to directly answer those questions. These are review recommendations only; no labels were changed.

No production retrieval code, defaults, metrics, question wording, existing report, or original label file was modified by this audit.
