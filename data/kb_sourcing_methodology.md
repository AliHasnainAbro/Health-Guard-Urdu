# Knowledge Base Sourcing Methodology

This file documents how each entry in `data/kb_documents.json` was sourced and authored.
It is **not** part of the RAG knowledge base itself — it exists for transparency, so
judges or reviewers can trace every claim back to its origin.

**General note on language:** WHO and WHO EMRO do not publish this specific health
content natively in Urdu. Every document's `content_urdu` field is original Urdu text
written by the project author, based on and faithful to the English-language facts
found in the sources below. No document in this knowledge base is `is_direct_urdu_source: true`.
This is disclosed per-document in the KB file itself, and repeated here for auditability.

Access date for all sources below: 3 September 2026.

**Link maintenance (4 September 2026):** the PAHO page "Debunking Immunization Myths"
(paho.org/en/topics/immunization/debunking-immunization-myths), previously cited by docs
#7, #8, #9 and #12, began returning 403 errors to all visitors (browser and automated
checks alike). All four citations were replaced with live WHO equivalents: the
"Vaccines and immunization: Vaccine safety" Q&A (docs #7, #8, #9) and the COVID-19
Mythbusters page (doc #12). Doc #9 moved out of the weak-citation set as a result —
see "Known weak points" below. The same day, the Johns Hopkins link in doc #5
(publichealth.jhu.edu/2013/klag-CIA-vaccination-cover-pakistan) also began returning
403 to all visitors and was replaced with The Guardian's original 11 July 2011 report
on the CIA fake vaccination drive.

---

### 1. پولیو ویکسین بانجھ پن کا سبب نہیں بنتی
- **Source**: Dawn / ReliefWeb, "Lab tests show polio vaccine is not 'Haram'" (14 Jan 2015)
- **URL**: reliefweb.int/report/pakistan/lab-tests-show-polio-vaccine-not-haram (mirrored at dawn.com/news/1156931)
- **Key facts used**: DRAP's National Control Laboratory for Biologicals (NCLB) tested three OPV batches (Novartis and GSK lots) for six possible human hormones; none were detected even at 0.0005mg sensitivity.
- **Translation/paraphrase notes**: Fully paraphrased into Urdu; no sentences copied from the source.

### 2. پولیو ویکسین حلال اور مذہبی طور پر جائز ہے
- **Source**: Same as #1 (NCLB testing also underpinned the halal determination)
- **URL**: reliefweb.int/report/pakistan/lab-tests-show-polio-vaccine-not-haram
- **Key facts used**: The 'Haram' rumor traced to 2004; NCLB testing and religious scholar endorsement were the response.
- **Translation/paraphrase notes**: Paraphrased; general reference to "علمائے کرام" (religious scholars) reflects widely reported scholar endorsement rather than one named individual.

### 3. بار بار قطرے پلانا نقصان دہ نہیں
- **Source**: WHO general guidance on OPV dosing safety (established public health consensus, not a single named document)
- **Translation/paraphrase notes**: Synthesized from general WHO/immunization-safety consensus; no single source URL.
- **Flag**: source is a consensus position, not one traceable document — weakest citation in the set. Consider strengthening if time allows.

### 4. پولیو ویکسین: بنیادی معلومات
- **Source**: WHO EMRO polio eradication program overview
- **URL**: emro.who.int/polio-eradication
- **Key facts used**: General polio disease/vaccination background, Pakistan's endemic status.
- **Translation/paraphrase notes**: General background paraphrase, not tied to a specific page's exact wording.

### 5. مغربی سازش کا الزام: حقیقت اور غلط فہمی
- **Sources**:
  - PMC6318131, "Polio in Pakistan: Political, Sociological, and Epidemiological Factors" (pmc.ncbi.nlm.nih.gov/articles/PMC6318131)
  - The Guardian, "CIA organised fake vaccination drive to get Osama bin Laden's DNA" (11 Jul 2011, theguardian.com/world/2011/jul/11/cia-fake-vaccinations-osama-bin-ladens-dna) — replaced a dead Johns Hopkins Bloomberg School link on 4 Sep 2026
  - Cross-referenced against doc #1's NCLB lab findings
- **Key facts used**: The CIA campaign was real and did fuel sterilization/HIV conspiracy narratives and violence against vaccinators; this is distinct from, and does not support, claims about current OPV ingredients.
- **Translation/paraphrase notes**: Carefully worded to acknowledge the real historical event without validating the false ingredient claim it fueled.

### 6. ویکسینز آٹزم کا سبب نہیں بنتیں
- **Source**: WHO Global Advisory Committee on Vaccine Safety (GACVS), statement of 11 Dec 2025
- **URL**: who.int/news/item/11-12-2025-who-expert-group-s-new-analysis-reaffirms-there-is-no-link-between-vaccines-and-autism
- **Key facts used**: Review of 31 studies (Jan 2010–Aug 2025); reaffirmed no causal link between vaccines (including thimerosal/aluminum) and ASD; reaffirms prior 2002/2004/2012 conclusions.
- **Translation/paraphrase notes**: Paraphrased; retracted-1998-study reference is well-established public record, not from this specific WHO statement.

### 7. ویکسین کے اجزاء نقصان دہ نہیں
- **Source**: WHO, "Vaccines and immunization: Vaccine safety" (Q&A, updated 23 Sep 2025) — ingredient safety (thiomersal, aluminium) and testing rigor sections
- **URL**: who.int/news-room/questions-and-answers/item/vaccines-and-immunization-vaccine-safety
- **Translation/paraphrase notes**: Paraphrased. Originally cited the PAHO "Debunking Immunization Myths" page; replaced 4 Sep 2026 after that page began returning 403 to all visitors.

### 8. ایک ساتھ کئی ویکسینز مدافعتی نظام کو کمزور نہیں کرتیں
- **Source**: Same as #7 (WHO vaccine safety Q&A)
- **Translation/paraphrase notes**: Paraphrased.

### 9. ویکسین کے بعد ہلکا بخار یا سوجن خطرناک نہیں
- **Source**: WHO, "Vaccines and immunization: Vaccine safety" Q&A (side effects and AEFI sections: "sore arm or a mild fever... minor and of short duration"); PMC7090020 review on vaccine safety monitoring
- **Note**: originally flagged as a weak consensus citation (no named document). Upgraded to a named WHO source on 4 Sep 2026 when the previously-linked PAHO page went dead — the Q&A's side-effects and AEFI sections directly support this document's content.

### 10. گھریلو ٹوٹکے وائرل بیماریوں کا علاج نہیں
- **Source**: Dubawa fact-check, "WHO did not approve COVID-19 herbal remedy with black pepper powder, ginger juice, others as ingredients"
- **URL**: dubawa.org/who-did-not-approve-covid-19-herbal-remedy-with-black-pepper-powder-ginger-juice-others-as-ingredients
- **Translation/paraphrase notes**: Paraphrased.

### 11. کالا زیرہ اور لہسن بیماریوں سے بچاؤ کی ضمانت نہیں
- **Source**: General public-health fact-checking consensus on garlic/black-seed prevention claims during COVID-19 (multiple fact-checkers, no single primary source)
- **Flag**: weakest citation in the set — general consensus, not one named document. Candidate to strengthen if time allows.

### 12. مستند علاج کی جگہ ٹوٹکوں پر انحصار خطرناک ہے
- **Sources**:
  - WHO COVID-19 Mythbusters (home remedies — pepper, supplements, and similar — do not prevent or cure COVID-19)
  - "A First Look at COVID-19 Messages on WhatsApp in Pakistan" (arxiv.org/html/2011.09145) — found ~20% of COVID-era Pakistani WhatsApp misinformation was bogus home remedies (basil seeds, salt/garlic gargles, honey-lemon tea, etc.)
- **Translation/paraphrase notes**: Paraphrased; statistic (~20%) is from the cited arXiv study, not fabricated.

---

## Known weak points (disclosed, not hidden)

Two documents (#3, #11) rest on general public-health consensus rather than one
specific, linkable primary source. This is disclosed here rather than papered over with
an invented citation. If time allows before the deadline, these are the first candidates
to strengthen with a named WHO page or peer-reviewed source. (Doc #9 was in this set
until 4 Sep 2026, when its dead PAHO citation was replaced with the WHO vaccine safety
Q&A — see the link maintenance note at the top.)

## Sources checked and deliberately NOT used

During review of an earlier draft, two citations were proposed but could not be verified
and were dropped rather than included on faith:
- `emro.who.int/polio/information-resources/iag-polio-meeting-adopts-plan.html` — appeared
  reused across multiple unrelated claims in a way inconsistent with its likely actual content.
- `PMC10222589` — could not be retrieved for verification (blocked by access wall); reused
  across unrelated claims in the same draft. Dropped rather than cited unverified.
