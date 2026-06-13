# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

**Student reviews of Northeastern University CS professors and courses.**

Official NEU sources (course catalogs, faculty bios) describe *what* a course covers
but never reflect teaching style, exam difficulty, weekly workload, grading strictness,
or whether a specific professor's section is worth taking. And students often hold back
honest reviews on official channels because they worry a negative review could affect
their grade or relationship with faculty. This knowledge lives in scattered unofficial
places — Rate My Professors, Coursicle, Reddit threads, Discord channels, Grad Café
posts — and is exactly the kind of corpus a RAG system can stitch together into a
useful, citation-grounded answer.

---

## Document Sources

The corpus contains **13 `.txt` files in `documents/`** drawn from 10 distinct unofficial
sources. Together they cover professor reputations, course difficulty, co-op outcomes,
and program-level reviews for the NEU CS / Khoury College community.

| # | Source | Type | URL or file path |
|---|--------|------|------------------|
| 1 | Rate My Professors — NEU CS dept | Professor ratings + reviews | https://www.ratemyprofessors.com/search/professors/696?q=*&did=11  →  `documents/ratemyprofessors_neu_cs.txt` |
| 2 | RateMyCourses — NEU | Course ratings (overall / easiness / interest / usefulness) | https://www.ratemycourses.io/neu  →  `documents/ratemycourses_neu.txt` |
| 3 | Coursicle — NEU CS catalog | Full Fall-2026 CS course listing | https://www.coursicle.com/neu/courses/CS/  →  `documents/coursicle_neu_cs_catalog.txt` |
| 4 | Coursicle — NEU professor directory | Faculty name index | https://www.coursicle.com/neu/professors/  →  `documents/coursicle_neu_professor_directory.txt` |
| 5 | Coursicle — CS 3500 (OOD) page | Per-course reviews + professor list | https://www.coursicle.com/neu/courses/CS/3500/  →  `documents/coursicle_cs3500_reviews.txt` |
| 6 | Coursicle — CS 4500 (Software Dev) page | Per-course reviews + professor list | https://www.coursicle.com/neu/courses/CS/4500/  →  `documents/coursicle_cs4500_reviews.txt` |
| 7 | Coursicle — multi-course review scrape (CS 2500/2510/3000/3650/5800) | Per-course professor rosters + review snippets | https://www.coursicle.com/neu/courses/CS/  →  `documents/coursicle_neu_cs_reviews.txt` |
| 8 | Reddit — r/NEU | Course/professor recommendation threads | https://www.reddit.com/r/NEU/search/?q=which+class+course+recommendation&sort=top  →  `documents/reddit_neu_course_recommendations.txt` |
| 9 | Reddit — r/cscareerquestions | NEU-tagged career-and-class threads | https://www.reddit.com/r/cscareerquestions/search/?q=which+professor+class+recommend  →  `documents/reddit_cscareerquestions_neu.txt` |
| 10 | NEU / Khoury Discord — #course-advice | Course-selection Q&A | `discord.gg/neu` (#khoury-courses / #cs-advice)  →  `documents/neu_discord_course_advice.txt` |
| 11 | Collegedunia — NEU MS CS reviews | Long-form grad-student reviews | https://s3.collegedunia.com/usa/university/1020-northeastern-university-boston/reviews  →  `documents/collegedunia_neu_reviews.txt` |
| 12 | The Grad Café — NEU CS threads | Grad-school discussion forum posts | https://forum.thegradcafe.com/search/?q=northeastern+computer+science  →  `documents/thegradcafe_neu_cs_threads.txt` |
| 13 | Studocu — NEU CS materials | Student-uploaded notes index | https://www.studocu.com/en-us/university/northeastern-university/computer-science/1290117  →  `documents/studocu_neu_cs_notes.txt` |

Notes:
- Sources **1, 2, 3, 4, 5, 6, 7** contain real scraped data (ratings, professor names, review snippets).
- Sources **8, 9, 10, 11, 12, 13** are JavaScript-rendered or login-walled and could not be fetched directly; their files contain representative content reflecting the kinds of discussions found on each platform, with explicit notes on how to populate them with real data via official APIs.

---

## Chunking Strategy

**Chunk size:** 300 tokens (max), measured by `tiktoken`'s `cl100k_base` encoder

**Overlap:** 50 tokens

**Splitter:** LangChain's `RecursiveCharacterTextSplitter` with a token-aware length
function. It tries to break on natural boundaries first — `\n\n`, then `\n`, then
sentence terminators (`. `, `! `, `? `), then spaces — so reviews are rarely cut
mid-sentence.

**Why these choices fit the documents:**
The corpus is **review-heavy**. Most chunks correspond to one professor's profile
block (rating + 5 reviews ≈ 200 tokens) or one Reddit/Discord Q&A thread on a single
course. 300 tokens is large enough to keep a professor's name, their rating, and
their representative reviews in the same chunk, but small enough that two different
professors' reviews don't get merged into one embedding — that mixing would dilute
the vector and make similarity search return ambiguous results. The 50-token
overlap protects against facts that straddle a chunk boundary (e.g. a professor's
name appears in one sentence and their grading policy is described two sentences
later); without overlap, a query for "Lieberherr's grading" might miss the chunk
that has his name but not his grading details.

**Preprocessing before chunking:**
- `.read_text(encoding="utf-8").strip()` to drop leading/trailing whitespace
- Empty files are skipped with a warning
- No HTML stripping was needed — all source files are already plain text

**Final chunk count: 61 chunks across 13 documents** (average ~219 tokens/chunk;
min 11, max 299). 61 is comfortably above the recommended ≥50-chunk floor —
chunks are small enough that semantic search can match precise queries without
losing per-professor focus.

---

## Sample Chunks

Five representative chunks pulled from five different source files. Each shows the
auto-generated `chunk_id` (which encodes both the source filename and the chunk's
position in that document) so attribution is reproducible.

### Sample 1 — `ratemyprofessors_neu_cs.txt_chunk_6`
**Source:** `ratemyprofessors_neu_cs.txt` · **Tokens:** 200 · **Position:** chunk 6 of 8

> Professor: Ferdinand Vesely
> Department: Computer Science
> Quality Rating: 3.0 / 5
> Number of Ratings: 48
> Would Take Again: 60%
> Difficulty: 3.2 / 5
> Courses Taught: CS 3100, CS 3500, CS 2500
> Student Reviews:
> - "Lecture notes, homework, labs, and tests all AI generated. Assignments felt very disconnected from lectures and often contained mistakes."
> - "3100 is a miserable experience and should be avoided but Ferd himself is a great professor. He is clearly very knowledgeable and passionate about CS."
> - "Great lectures and you can tell he loves CS. His lectures are very clear."
> - "The class is designed by AI and not made by him, and he made it clear that he doesn't appreciate how the curriculum is designed either."
> - "Ferd is a great guy and very knowledgeable. Unfortunately the new CS3100 curriculum is fully AI slop."

### Sample 2 — `coursicle_cs3500_reviews.txt_chunk_1`
**Source:** `coursicle_cs3500_reviews.txt` · **Tokens:** 292 · **Position:** chunk 1 of 3

> --- STUDENT REVIEWS ---
>
> Review — Professor: Benjamin Lerner | Student Year: Junior | ~3 years ago
> "Self-evaluations were due the day after each homework submission — if you miss the self-evaluation you receive a zero on that assignment, which really disrupted my schedule. Be aware of the self-eval deadline system."
>
> Review — Professor: Mark Fontenot | Student Year: First-year | ~2 years ago
> "Classes were pretty much useless. The instructor arrived late, read off the slides, and ended early. … Programming assignments averaged about 15 hours of work each, but they were substantive and you do learn from them."
>
> Review — Professor: Vidoje Mihajlovikj (Vido)
> Vido is specifically praised by students for giving strong, useful exam reviews. Students recommend taking him for CS 3500 if his section is available. One review cited on RateMyCourses stated: "Take Vido if you can — his exam reviews are the best and really prepare you for the tests."
>
> --- RATE MY COURSES DATA FOR CS 3500 ---
> Overall: 4.3 / 5 · Easiness: 2.6 / 5 · Interest: 4.1 / 5 · Usefulness: 4.9 / 5

### Sample 3 — `neu_discord_course_advice.txt_chunk_3`
**Source:** `neu_discord_course_advice.txt` · **Tokens:** 201 · **Position:** chunk 3 of 5

> Q: "Can I skip CS 2500 if I already know Java?"
> Common responses:
> - No — the department will not let you skip it without a waiver, and waivers are rarely granted.
> - Even if you know Java, Fundies teaches a completely different programming paradigm (functional, bottom-up design).
> - Students who skip it via waiver often struggle in CS 2510 and CS 3500 because they missed the design recipe foundation.
>
> Q: "What do students think about Matthias Felleisen?"
> Common responses:
> - He's a legend in the programming languages world — co-created Racket and wrote HtDP.
> - His classes are challenging (4.4/5 difficulty on RMP) but his grading is more lenient than you'd expect (85% = A).
> - Some students love his engaging lecture style; others find him disorganized or high-ego.
> - Worth taking at least one course with him for the perspective, especially if you're interested in PL or compilers.

### Sample 4 — `reddit_neu_course_recommendations.txt_chunk_2`
**Source:** `reddit_neu_course_recommendations.txt` · **Tokens:** 179 · **Position:** chunk 2 of 5

> Topic: Fundies 1 and 2 survival tips
> Students share advice for CS 2500 and CS 2510:
> - "Start the design recipe drills early — Fundies is not about syntax, it's about structured problem solving."
> - "Olin Shivers is legendary — if his section is open, take it. His anecdotes alone make the 90-minute lectures worth it."
> - "Benjamin Lerner is tough but fair. He will push you harder than any other Fundies professor but you'll come out a much stronger programmer."
> - "Leena Razzaq is hit or miss — some students say she explained concepts clearly, others felt she read off slides. Check RMP before registering."
> - "CS 2510 is harder than 2500 — the jump to Java OOP after Racket is rough. Give yourself extra time in the first two weeks."

### Sample 5 — `thegradcafe_neu_cs_threads.txt_chunk_2`
**Source:** `thegradcafe_neu_cs_threads.txt` · **Tokens:** 241 · **Position:** chunk 2 of 5

> Post Type: First Semester Advice
> "If I could give one piece of advice to incoming Khoury MS students: do not underestimate the core courses. CS 5004 (OOD) and CS 5800 (Algorithms) in the same semester is a brutal combination. I did it and barely survived. Take one of them in your first semester and one in your second if possible."
>
> Post Type: Co-op Process Walkthrough
> "The co-op process at NEU works like this: Khoury posts available positions on NUworks, you apply, interview, and if selected you defer your courses for a 6-month rotation. The co-op office runs prep workshops on resume writing and technical interviews."
>
> Post Type: Grading Culture
> "Grading at Khoury is strict but transparent. Most courses have detailed rubrics. The professors who are toughest on grades (Felleisen, Lerner) are also the ones whose courses teach you the most."

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**

**Production tradeoff reflection:**

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**

**How source attribution is surfaced in the response:**

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**

**What the system returned:**

**Root cause (tied to a specific pipeline stage):**

**What you would change to fix it:**

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**

**One way your implementation diverged from the spec, and why:**

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*

**Instance 2**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*
