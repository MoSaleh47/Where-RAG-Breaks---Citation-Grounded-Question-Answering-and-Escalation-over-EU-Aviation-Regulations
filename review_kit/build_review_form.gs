/**
 * ============================================================================
 *  PFE - Revue du benchmark / Benchmark review  (Reg. (EU) No 376/2014)
 *  RESUMABLE BUILDER v2
 * ============================================================================
 *
 *  WHY v2: Google kills any Apps Script run at 6 minutes. v1 made ~231 API
 *  calls and only printed the links at the very end, so a slow run showed
 *  nothing at all. v2 fixes that three ways:
 *    - the form and its links are created and LOGGED FIRST, within seconds;
 *    - the 4 validity questions are one grid instead of 4 items (~40% fewer calls);
 *    - progress is saved, so if it runs out of time you just RUN IT AGAIN
 *      and it picks up exactly where it stopped.
 *
 *  HOW TO USE
 *   1. https://script.google.com -> New project
 *   2. Delete the sample code, paste THIS ENTIRE FILE, Save
 *   3. Run > buildReviewForm
 *   4. The links appear in the log within a few seconds. Keep them.
 *   5. If the log ends with "RUN buildReviewForm AGAIN", just run it again.
 *      Repeat until it prints "BUILD COMPLETE". Usually 1-2 runs.
 *
 *  Starting over? Delete the form in Drive, then Run > resetReviewForm.
 * ============================================================================
 */

var BLOCK_SIZE = 6;
var TIME_BUDGET_MS = 240000;   // stop at 4 min, leaving margin under Google's 6

var ROWS = [
 {
  "qa_id": "QA_0003",
  "source_class": "GM",
  "question_type": "obligation",
  "difficulty": "medium",
  "review_reason": "exception_record",
  "split": "excluded",
  "question": "Am I under the legal obligation to report occurrences?",
  "reference_answer": "Yes, individuals are under a legal obligation to report occurrences as specified in Section 2.2 of the regulation.",
  "citation": "Section 2.2",
  "gold_child_ids": "",
  "evidence": ""
 },
 {
  "qa_id": "QA_0011",
  "source_class": "ARTICLE",
  "question_type": "definition",
  "difficulty": "easy",
  "review_reason": "exception_record",
  "split": "development",
  "question": "What subject matter is laid down in Article 3(1) of Regulation (EU) No 376/2014?",
  "reference_answer": "Article 3(1) lays down rules on occurrence reporting; analysis and follow-up; protection of aviation professionals; appropriate use of safety information; integration into the European Central Repository; and dissemination of anonymised information to improve aviation safety.",
  "citation": "Article 3(1)",
  "gold_child_ids": "EU_376_2014_ART_3__C0001;EU_376_2014_ART_3__C0002;EU_376_2014_ART_3__C0003;EU_376_2014_ART_3__C0004;EU_376_2014_ART_3__C0005;EU_376_2014_ART_3__C0006;EU_376_2014_ART_3__C0007",
  "evidence": "EU_376_2014_ART_3__C0001 [Article 3(1)]: 1.This Regulation lays down rules on:\nEU_376_2014_ART_3__C0002 [Article 3(1)(a)]: (a)the reporting of occurrences which endanger or which, if not corrected or addressed, would endanger an aircraft, its occupants, any other person, equipment or installation affecting aircraft operations; and the reporting of other relevant safety-related information in that context;\nEU_376_2014_ART_3__C0003 [Article 3(1)(b)]: (b)analysis and follow-up action in respect of reported occurrences and other safety-related information;\nEU_376_2014_ART_3__C0004 [Article 3(1)(c)]: (c)the protection of aviation professionals;\nEU_376_2014_ART_3__C0005 [Article 3(1)(d)]: (d)appropriate use collected safety information;\nEU_376_2014_ART_3__C0006 [Article 3(1)(e)]: (e)the integration of information into the European Central Repository; and\nEU_376_2014_ART_3__C0007 [Article 3(1)(f)]: (f)the dissemination of anonymised information to interested parties for the purpose of providing such parties with the information they need in order to improve aviation safety."
 },
 {
  "qa_id": "QA_0040",
  "source_class": "ARTICLE",
  "question_type": "timeline",
  "difficulty": "medium",
  "review_reason": "stratified_unchanged_ARTICLE_test",
  "split": "test",
  "question": "What is the timeline for transmitting information about requests to the Commission?",
  "reference_answer": "The information regarding each request and the action taken must be transmitted in a timely manner to the Commission whenever a request is received and/or action is taken.",
  "citation": "Article 12(1)",
  "gold_child_ids": "EU_376_2014_ART_12__C0002;EU_376_2014_ART_12__C0001",
  "evidence": "EU_376_2014_ART_12__C0002 [Article 12(1)]: That information shall be transmitted in a timely manner to the Commission whenever a request is received and/or action is taken.\nEU_376_2014_ART_12__C0001 [Article 12(1)]: 1.The point of contact shall record each request received and the action taken pursuant to that request."
 },
 {
  "qa_id": "QA_0047",
  "source_class": "ARTICLE",
  "question_type": "obligation",
  "difficulty": "easy",
  "review_reason": "stratified_unchanged_ARTICLE_development",
  "split": "development",
  "question": "What measures must Member States and organisations take regarding the confidentiality of occurrence details?",
  "reference_answer": "Member States and organisations, in accordance with their national law, and the Agency shall take the necessary measures to ensure the appropriate confidentiality of the details of occurrences received by them. This is mandated by Article 15(1).",
  "citation": "Article 15(1)",
  "gold_child_ids": "EU_376_2014_ART_15__C0001;EU_376_2014_ART_15__C0002",
  "evidence": "EU_376_2014_ART_15__C0001 [Article 15(1)]: 1.Member States and organisations, in accordance with their national law, and the Agency shall take the necessary measures to ensure the appropriate confidentiality of the details of occurrences received by them pursuant to Articles 4, 5 and 10.\nEU_376_2014_ART_15__C0002 [Article 15(1)]: Each Member State, each organisation established in a Member State, or the Agency shall process personal data only to the extent necessary for the purposes of this Regulation and without prejudice to national legal acts implementing Directive 95/46/EC."
 },
 {
  "qa_id": "QA_0058",
  "source_class": "ARTICLE",
  "question_type": "obligation",
  "difficulty": "easy",
  "review_reason": "stratified_unchanged_ARTICLE_development",
  "split": "development",
  "question": "What must the Commission do after adopting a delegated act?",
  "reference_answer": "As soon as it adopts a delegated act, the Commission shall notify it simultaneously to the European Parliament and to the Council. This notification is a requirement following the adoption of the act.",
  "citation": "Article 18(4)",
  "gold_child_ids": "EU_376_2014_ART_18__C0004",
  "evidence": "EU_376_2014_ART_18__C0004 [Article 18(4)]: 4.As soon as it adopts a delegated act, the Commission shall notify it simultaneously to the European Parliament and to the Council."
 },
 {
  "qa_id": "QA_0062",
  "source_class": "ARTICLE",
  "question_type": "scope",
  "difficulty": "medium",
  "review_reason": "exception_record",
  "split": "test",
  "question": "How does Regulation (EU) No 376/2014 interact with rules on access to documents and personal-data protection?",
  "reference_answer": "Except for the stricter access rules in Articles 10 and 11, Regulation (EU) No 376/2014 applies without prejudice to Regulation (EC) No 1049/2001. It also applies without prejudice to national measures implementing Directive 95/46/EC and in accordance with Regulation (EC) No 45/2001.",
  "citation": "Article 20(1)-(2)",
  "gold_child_ids": "EU_376_2014_ART_20__C0001;EU_376_2014_ART_20__C0002",
  "evidence": "EU_376_2014_ART_20__C0001 [Article 20(1)]: 1.With the exception of Articles 10 and 11, which establish stricter rules on access to the data and information contained in the European Central Repository, this Regulation shall apply without prejudice to Regulation (EC) No 1049/2001.\nEU_376_2014_ART_20__C0002 [Article 20(2)]: 2.This Regulation shall apply without prejudice to national legal acts implementing Directive 95/46/EC and in accordance with Regulation (EC) No 45/2001."
 },
 {
  "qa_id": "QA_0063",
  "source_class": "ARTICLE",
  "question_type": "exception",
  "difficulty": "easy",
  "review_reason": "hybrid_k20_residual",
  "split": "test",
  "question": "What exceptions are noted in Regulation (EU) No 376/2014?",
  "reference_answer": "Articles 10 and 11 of Regulation (EU) No 376/2014 establish stricter rules on access to the data and information contained in the European Central Repository, which are exceptions to the general application of the Regulation.",
  "citation": "Article 20(1)",
  "gold_child_ids": "EU_376_2014_ART_20__C0001",
  "evidence": "EU_376_2014_ART_20__C0001 [Article 20(1)]: 1.With the exception of Articles 10 and 11, which establish stricter rules on access to the data and information contained in the European Central Repository, this Regulation shall apply without prejudice to Regulation (EC) No 1049/2001."
 },
 {
  "qa_id": "QA_0071",
  "source_class": "ANNEX",
  "question_type": "obligation",
  "difficulty": "medium",
  "review_reason": "stratified_unchanged_ANNEX_test",
  "split": "test",
  "question": "What must organisations, Member States, and the Agency ensure when entering occurrence reports in their databases?",
  "reference_answer": "They must ensure that occurrence reports recorded in their databases contain at least the common mandatory data fields, which include information such as Headline, Filing Information, Date, Location, Classification, Narrative, Events, and Risk classification. This applies to both mandatorily reported and, to the best extent possible, voluntarily reported occurrences.",
  "citation": "Section 1",
  "gold_child_ids": "EU_376_2014_ANNEX_I__C0003",
  "evidence": "EU_376_2014_ANNEX_I__C0003 [Annex I, item 1]: When entering, in their respective databases, information on every occurrence mandatorily reported and, to the best extent possible, every occurrence voluntarily reported, organisations, Member States and the Agency must ensure that occurrence reports recorded in their databases contain at least the following information:"
 },
 {
  "qa_id": "QA_0080",
  "source_class": "ANNEX",
  "question_type": "obligation",
  "difficulty": "medium",
  "review_reason": "exception_record;hybrid_k20_residual",
  "split": "test",
  "question": "Does the activity category under which an occurrence is listed limit whether it must be reported?",
  "reference_answer": "No. The Annex groups occurrences under activities where they are normally observed, but an occurrence must still be reported when it takes place outside the category under which it is listed.",
  "citation": "Annex I, Remark",
  "gold_child_ids": "EU_2015_1018_ANNEX_I__C0001",
  "evidence": "EU_2015_1018_ANNEX_I__C0001 [Annex I]: Remark: This Annex is structured in such a way that the pertinent occurrences are linked with categories of activities during which they are normally observed, according to experience, in order to facilitate the reporting of those occurrences. However, this presentation must not be understood as meaning that occurrences must not be reported in case they take place outside the category of activities to which they are linked in the list."
 },
 {
  "qa_id": "QA_0081",
  "source_class": "ANNEX",
  "question_type": "scope",
  "difficulty": "medium",
  "review_reason": "stratified_unchanged_ANNEX_test",
  "split": "test",
  "question": "What is included in the category of 'Take-off and landing' occurrences?",
  "reference_answer": "The 'Take-off and landing' category includes occurrences such as taxiway or runway excursions, rejected take-offs, and inability to achieve required performance during take-off or landing. It also covers incidents like incorrect configuration settings during take-off or landing.",
  "citation": "ANNEX I, 1.3",
  "gold_child_ids": "EU_2015_1018_ANNEX_I__C0014;EU_2015_1018_ANNEX_I__C0015",
  "evidence": "EU_2015_1018_ANNEX_I__C0014 [Annex I, item 1.3.5]: (5)Inability to achieve required or expected performance during take-off, go-around or landing.\nEU_2015_1018_ANNEX_I__C0015 [Annex I, item 1.3.6]: (6)Actual or attempted take-off, approach or landing with incorrect configuration setting."
 },
 {
  "qa_id": "QA_0083",
  "source_class": "ANNEX",
  "question_type": "obligation",
  "difficulty": "medium",
  "review_reason": "exception_record",
  "split": "test",
  "question": "Which maintenance-related occurrence is listed in Annex II, item 3.14?",
  "reference_answer": "The listed occurrence is releasing an aircraft to service from maintenance where there is non-compliance that endangers flight safety.",
  "citation": "Annex II, item 3.14",
  "gold_child_ids": "EU_2015_1018_ANNEX_II__C0022",
  "evidence": "EU_2015_1018_ANNEX_II__C0022 [Annex II, item 3.14]: (14)Releasing an aircraft to service from maintenance in case of any non-compliance which endangers the flight safety."
 },
 {
  "qa_id": "QA_0097",
  "source_class": "ARTICLE",
  "question_type": "timeline",
  "difficulty": "easy",
  "review_reason": "stratified_unchanged_ARTICLE_test",
  "split": "test",
  "question": "From when does Regulation (EU) 2020/2034 apply?",
  "reference_answer": "This Regulation shall apply from 1 January 2021.",
  "citation": "Article 4",
  "gold_child_ids": "EU_2020_2034_ART_4__C0002;EU_2020_2034_ART_4__C0003;EU_2020_2034_ART_4__C0001;EU_2020_2034_ART_4__C0004",
  "evidence": "EU_2020_2034_ART_4__C0002 [Article 4]: It shall apply from 1 January 2021.\nEU_2020_2034_ART_4__C0003 [Article 4]: This Regulation shall be binding in its entirety and directly applicable in all Member States.\nEU_2020_2034_ART_4__C0001 [Article 4]: This Regulation shall enter into force on the twentieth day following that of its publication in the Official Journal of the European Union.\nEU_2020_2034_ART_4__C0004 [Article 4]: Done at Brussels, 6 October 2020."
 },
 {
  "qa_id": "QA_0163",
  "source_class": "GM",
  "question_type": "obligation",
  "difficulty": "medium",
  "review_reason": "stratified_unchanged_GM_test",
  "split": "test",
  "question": "What is the key principle regarding the reporting of occurrences?",
  "reference_answer": "The key principle is that reporting an occurrence through the reporting system of their organisation should be promoted and recognised as the normal channel for aviation professionals. However, direct reporting to a competent authority is not prevented if the reporter lacks confidence in their organisation's reporting system.",
  "citation": "Article 4(6)",
  "gold_child_ids": "GM_EU_376_2014_SEC_2_8__C0005;GM_EU_376_2014_SEC_2_8__C0009",
  "evidence": "GM_EU_376_2014_SEC_2_8__C0005 [GM 2.8]: Key principle Reporting an occurrence through the reporting system of their organisation should be promoted and recognised as the normal channel of reporting for aviation professionals.\nGM_EU_376_2014_SEC_2_8__C0009 [GM 2.8]: Whereas the most direct reporting channel should be preferred (the organisation’s reporting system) and even promoted, it is understood that direct reporting to a competent authority by a person employed by an organisation or whose services are contracted or used by this organisation is not prevented. Indeed, situations may occur where reporters are not confident in the reporting system of their organisations and may wish to use another reporting channel. This is consistent with the objective of fostering a ‘Just Culture’ which is pursued by Regulation 376/2014. It aims, in particular, at ensuring confidence of aviation professionals in occurrence reporting systems and encourages them to reports any relevant safety information with a view to contribute to the enhancement of aviation safety and accidents prevention."
 },
 {
  "qa_id": "QA_0176",
  "source_class": "GM",
  "question_type": "obligation",
  "difficulty": "easy",
  "review_reason": "exception_record;hybrid_k20_residual",
  "split": "test",
  "question": "What does Regulation 376/2014 require organisations to do with occurrence information?",
  "reference_answer": "It requires organisations to collect, analyse and follow up occurrences as part of their safety management systems and to transfer certain occurrences to their competent authority.",
  "citation": "GM 3.1",
  "gold_child_ids": "GM_EU_376_2014_SEC_3_1__C0001;GM_EU_376_2014_SEC_3_1__C0002",
  "evidence": "GM_EU_376_2014_SEC_3_1__C0001 [GM 3.1]: See also Sections 1.1 and 2.1. The collection, analysis and follow-up of occurrences are part of organisations safety management systems. It contributes to the identification of risks and to the adoption of relevant mitigation actions by organisations.\nGM_EU_376_2014_SEC_3_1__C0002 [GM 3.1]: Regulation 376/2014 requires the collection, analysis and follow-up by organisations, as well as the transfer of certain occurrences to their competent authority. One could question the safety benefit of transferring this information to the competent authority. Indeed the organisation has already addressed its safety risks in the context of its SMS."
 },
 {
  "qa_id": "QA_0183",
  "source_class": "GM",
  "question_type": "timeline",
  "difficulty": "medium",
  "review_reason": "exception_record",
  "split": "test",
  "question": "When does the reporting period start for design or production organisations?",
  "reference_answer": "For design or production organisations, the reporting period starts when the process of identifying an unsafe or potentially unsafe condition concludes. The 72-hour reporting period is counted from that point.",
  "citation": "GM 3.4",
  "gold_child_ids": "GM_EU_376_2014_SEC_3_4__C0005;GM_EU_376_2014_SEC_3_4__C0006",
  "evidence": "GM_EU_376_2014_SEC_3_4__C0005 [GM 3.4]: This reporting flow starts from the moment the occurrence is detected (T0). From this moment, the individual shall report it to the organisation or to the authority as soon as possible, but before 72 hours if it falls within the mandatory scheme. In this case, the organisation has 72 hours to report to the authority from the moment they become aware of the occurrence.\nGM_EU_376_2014_SEC_3_4__C0006 [GM 3.4]: It should be understood that in certain specific situations the identification of the occurrence might require an additional stage before this reporting flow starts. In particular, for Design or Production Organisations the time start (T0) is the moment where the individuals carrying out this process in the organisation identify the unsafe or the potential unsafe condition. Therefore, these organisations will have 72 hours to report to the competent authority when this process concludes that an occurrence represents an unsafe or potential unsafe condition as per Annex Part 21 of Regulation 748/2012."
 },
 {
  "qa_id": "QA_0193",
  "source_class": "GM",
  "question_type": "obligation",
  "difficulty": "medium",
  "review_reason": "exception_record",
  "split": "test",
  "question": "What should organisations aim to provide in their initial occurrence report?",
  "reference_answer": "They should make the initial report as complete as possible, especially its safety assessment, because not every report will receive a follow-up report.",
  "citation": "GM 3.9",
  "gold_child_ids": "GM_EU_376_2014_SEC_3_9__C0006",
  "evidence": "GM_EU_376_2014_SEC_3_9__C0006 [GM 3.9]: It is recognised that some of the requested information might necessitate detailed assessment or analysis (e.g. risk classification) and might only be available after the occurrence has been analysed. It is also recognised that the period required for the notification of the occurrence might not allow the organisation to provide complete information within its initial notification. However, organisations should aim to provide the initial report as complete as possible, notably in regards to the safety assessment, as not all reports may be subject to follow-up report."
 },
 {
  "qa_id": "QA_0213",
  "source_class": "GM",
  "question_type": "obligation",
  "difficulty": "medium",
  "review_reason": "exception_record",
  "split": "test",
  "question": "How should a competent authority handle occurrences reported by organisations and individuals?",
  "reference_answer": "It should handle occurrences reported under Regulation 376/2014 in the same manner whether they are mandatory or voluntary, including occurrences reported directly by individuals.",
  "citation": "GM 4.2",
  "gold_child_ids": "GM_EU_376_2014_SEC_4_2__C0003;GM_EU_376_2014_SEC_4_2__C0004",
  "evidence": "GM_EU_376_2014_SEC_4_2__C0003 [GM 4.2]: Key principle All occurrences reported by an organisation to its competent authority in application of Regulation 376/2014 and its implementing rules shall be handled and addressed in the same manner by this competent authority. All occurrences directly by an individual reporter to a competent authority, whether or not it is reported on the basis of Regulation 2015/1018, shall be handled and addressed in the same manner by that competent authority In general, Regulation 376/2014 does not differentiate the way mandatorily reportable and voluntarily reportable occurrences shall be addressed by the competent authority. It does, however, impose differentiated requirements to the competent authority for handling, from one side, occurrences transferred by an organisation and, from the other side, occurrences directly reported by an individual.\nGM_EU_376_2014_SEC_4_2__C0004 [GM 4.2]: All information collected from organisations, whether it was reported in application of Article 4 or of Article 5, is subject to similar handling by the competent authority. And all information directly reported by individuals to the competent authority, whether it was reported in application of Article 4 or of Article 5, is subject to the same analysis and follow-up obligations."
 },
 {
  "qa_id": "QA_0229",
  "source_class": "GM",
  "question_type": "obligation",
  "difficulty": "medium",
  "review_reason": "stratified_unchanged_GM_test",
  "split": "test",
  "question": "What principle is established in Article 16(11) regarding internal rules?",
  "reference_answer": "Article 16(11) sets the obligation for organisations to adopt internal rules describing how ‘Just Culture’ principles are guaranteed and implemented within that organisation after consulting its staff representatives.",
  "citation": "Article 16(11)",
  "gold_child_ids": "GM_EU_376_2014_SEC_4_9__C0002",
  "evidence": "GM_EU_376_2014_SEC_4_9__C0002 [GM 4.9]: Article 16(6) states the principle of proceedings limitations; Article 16(9) establishes the principle of non-prejudice in a corporate context, both principles being subject to the two exceptions mentioned in Article 16(10). Article 16(11) sets the obligation for organisations to adopt, after consulting its staff representatives, internal rules describing how ‘Just Culture’ principles are guaranteed and implemented within that organisation."
 },
 {
  "qa_id": "QA_0235",
  "source_class": "GM",
  "question_type": "responsibility",
  "difficulty": "medium",
  "review_reason": "stratified_unchanged_GM_development",
  "split": "development",
  "question": "What is the role of the Commission regarding the classification of occurrences?",
  "reference_answer": "The Commission was required to adopt a list classifying occurrences to be referred to, which is outlined in Article 4(5). This list helps identify occurrences that are mandatory to report due to their significant risk to aviation safety.",
  "citation": "Article 4(5)",
  "gold_child_ids": "GM_EU_376_2014_SEC_5_3__C0003",
  "evidence": "GM_EU_376_2014_SEC_5_3__C0003 [GM 5.3]: The occurrences to be reported in the context of mandatory reporting systems are those which may represent a significant risk to aviation safety and which fall into defined categories (Article 4(1)). To facilitate the identification of those occurrences, the Commission was required to adopt a list classifying occurrences to be referred to (Article 4(5))."
 },
 {
  "qa_id": "QA_0248",
  "source_class": "ARTICLE",
  "question_type": "exception",
  "difficulty": "hard",
  "review_reason": "exception_record",
  "split": "development",
  "question": "Who must report when the pilot in command is unable to report an occurrence?",
  "reference_answer": "When the pilot in command is unable to report, another crew member next in the chain of command must report the occurrence, subject to the aircraft and operator scope stated in Article 4(6)(a).",
  "citation": "Article 4(6)(a)",
  "gold_child_ids": "EU_376_2014_ART_4__C0030",
  "evidence": "EU_376_2014_ART_4__C0030 [Article 4(6)(a)]: (a)the pilot in command, or, in cases where the pilot in command is unable to report the occurrence, any other crew member next in the chain of command of an aircraft registered in a Member State or an aircraft registered outside the Union but used by an operator for which a Member State ensures oversight of operations or an operator established in the Union;"
 },
 {
  "qa_id": "QA_0258",
  "source_class": "ARTICLE",
  "question_type": "scope",
  "difficulty": "hard",
  "review_reason": "exception_record",
  "split": "development",
  "question": "What information must competent authorities store in the national database?",
  "reference_answer": "They must store occurrence reports drawn up from details collected under Articles 4 and 5. Relevant information on accidents and serious incidents collected or issued by safety investigation authorities must also be stored there.",
  "citation": "Article 6(6)-(7)",
  "gold_child_ids": "EU_376_2014_ART_6__C0014;EU_376_2014_ART_6__C0015",
  "evidence": "EU_376_2014_ART_6__C0014 [Article 6(6)]: 6.The competent authorities referred to in paragraph 3 shall store occurrence reports drawn up on the basis of details of occurrences collected in accordance with Articles 4 and 5 in a national database.\nEU_376_2014_ART_6__C0015 [Article 6(7)]: 7.Relevant information on accidents and serious incidents collected or issued by safety investigation authorities shall also be stored in the national database."
 },
 {
  "qa_id": "QA_0263",
  "source_class": "ARTICLE",
  "question_type": "cross_reference",
  "difficulty": "hard",
  "review_reason": "exception_record",
  "split": "test",
  "question": "What database-format requirements and support responsibilities are specified in Article 7(4) and Article 7(8)?",
  "reference_answer": "The relevant databases must use formats that are standardised for information exchange and compatible with ECCAIRS and the ADREP taxonomy. The Commission and the Agency must support Member-State competent authorities with data integration and provide that support in a way that contributes to harmonised data entry.",
  "citation": "Article 7(4) and 7(8)",
  "gold_child_ids": "EU_376_2014_ART_7__C0004;EU_376_2014_ART_7__C0005;EU_376_2014_ART_7__C0006;EU_376_2014_ART_7__C0011;EU_376_2014_ART_7__C0015",
  "evidence": "EU_376_2014_ART_7__C0004 [Article 7(4)]: 4.The databases referred to in paragraphs 5, 6 and 8 of Article 6 shall use formats which are:\nEU_376_2014_ART_7__C0005 [Article 7(4)(a)]: (a)standardised to facilitate information exchange; and\nEU_376_2014_ART_7__C0006 [Article 7(4)(b)]: (b)compatible with the ECCAIRS software and the ADREP taxonomy.\nEU_376_2014_ART_7__C0011 [Article 7(8)]: 8.The Commission and the Agency shall support the competent authorities of the Member States in their task of data integration, including for example in:\nEU_376_2014_ART_7__C0015 [Article 7(8)(c)]: The Commission and the Agency shall provide that support in such a way as to contribute to the harmonisation of the data entry process across Member States, in particular by providing to staff working in the bodies or entities referred to in Article 6(1), (3) and (4):"
 },
 {
  "qa_id": "QA_0265",
  "source_class": "ARTICLE",
  "question_type": "obligation",
  "difficulty": "hard",
  "review_reason": "exception_record",
  "split": "development",
  "question": "What must an organisation do after its analysis identifies appropriate corrective or preventive action for a safety deficiency?",
  "reference_answer": "It must implement the action in a timely manner and establish a process to monitor its implementation and effectiveness.",
  "citation": "Article 13(2)",
  "gold_child_ids": "EU_376_2014_ART_13__C0003;EU_376_2014_ART_13__C0004;EU_376_2014_ART_13__C0005",
  "evidence": "EU_376_2014_ART_13__C0003 [Article 13(2)]: 2.When, following the analysis referred to in paragraph 1, an organisation established in a Member State identifies any appropriate corrective or preventive action required to address actual or potential aviation safety deficiencies, it shall:\nEU_376_2014_ART_13__C0004 [Article 13(2)(a)]: (a)implement that action in a timely manner; and\nEU_376_2014_ART_13__C0005 [Article 13(2)(b)]: (b)establish a process to monitor the implementation and effectiveness of the action."
 },
 {
  "qa_id": "QA_0272",
  "source_class": "ARTICLE",
  "question_type": "exception",
  "difficulty": "hard",
  "review_reason": "exception_record",
  "split": "development",
  "question": "For what purposes may information derived from occurrence reports be used under Article 15(2)?",
  "reference_answer": "It may be used only for the purpose for which it was collected. Member States, the Agency and organisations must not use or make occurrence information available to attribute blame or liability, or for a purpose other than maintaining or improving aviation safety.",
  "citation": "Article 15(2)",
  "gold_child_ids": "EU_376_2014_ART_15__C0003;EU_376_2014_ART_15__C0004;EU_376_2014_ART_15__C0005;EU_376_2014_ART_15__C0006",
  "evidence": "EU_376_2014_ART_15__C0003 [Article 15(2)]: 2.Without prejudice to the provisions relating to the protection of safety information in Articles 12, 14 and 15 of Regulation (EU) No 996/2010, information derived from occurrence reports shall be used only for the purpose for which it has been collected.\nEU_376_2014_ART_15__C0004 [Article 15(2)]: Member States, the Agency and organisations shall not make available or use the information on occurrences:\nEU_376_2014_ART_15__C0005 [Article 15(2)(a)]: (a)in order to attribute blame or liability; or\nEU_376_2014_ART_15__C0006 [Article 15(2)(b)]: (b)for any purpose other than the maintenance or improvement of aviation safety."
 },
 {
  "qa_id": "QA_0277",
  "source_class": "ARTICLE",
  "question_type": "obligation",
  "difficulty": "hard",
  "review_reason": "exception_record",
  "split": "development",
  "question": "What must Member States do regarding personal details and disidentified information in national occurrence databases?",
  "reference_answer": "Member States must ensure that personal details are never recorded in the national database referred to in Article 6(6), and must make the disidentified information available to relevant parties so they can discharge aviation-safety improvement obligations.",
  "citation": "Article 16(3)",
  "gold_child_ids": "EU_376_2014_ART_16__C0004",
  "evidence": "EU_376_2014_ART_16__C0004 [Article 16(3)]: 3.Each Member State shall ensure that no personal details are ever recorded in the national database referred to in Article 6(6). Such disidentified information shall be made available to all relevant parties, for example to allow them to discharge their obligations in relation to aviation safety improvement."
 },
 {
  "qa_id": "QA_0278",
  "source_class": "ARTICLE",
  "question_type": "cross_reference",
  "difficulty": "hard",
  "review_reason": "exception_record",
  "split": "development",
  "question": "What duties do organisations and the designated Member-State body have in implementing just-culture protections?",
  "reference_answer": "After consulting staff representatives, each organisation must adopt internal rules describing how just-culture principles, particularly paragraph 9, are guaranteed and implemented. The body designated by the Member State is responsible for implementing paragraphs 6, 9 and 11 and may ask to review those internal rules before implementation.",
  "citation": "Article 16(11)-(12)",
  "gold_child_ids": "EU_376_2014_ART_16__C0019;EU_376_2014_ART_16__C0020;EU_376_2014_ART_16__C0021",
  "evidence": "EU_376_2014_ART_16__C0019 [Article 16(11)]: 11.Each organisation established in a Member State shall, after consulting its staff representatives, adopt internal rules describing how ‘just culture’ principles, in particular the principle referred to in paragraph 9, are guaranteed and implemented within that organisation.\nEU_376_2014_ART_16__C0020 [Article 16(11)]: The body designated pursuant to paragraph 12 may ask to review the internal rules of the organisations established in its Member State before those internal rules are implemented.\nEU_376_2014_ART_16__C0021 [Article 16(12)]: 12.Each Member State shall designate a body responsible for the implementation of paragraphs 6, 9 and 11."
 },
 {
  "qa_id": "QA_0279",
  "source_class": "ARTICLE",
  "question_type": "scope",
  "difficulty": "hard",
  "review_reason": "exception_record",
  "split": "development",
  "question": "When must Member States refrain from proceedings for reported infringements, and when do the paragraph 10 exceptions apply?",
  "reference_answer": "Subject to national criminal law, Member States must refrain from proceedings for unpremeditated or inadvertent infringements known only because they were reported under Articles 4 and 5. The protection need not apply in cases of wilful misconduct or manifest, severe and serious disregard of an obvious risk accompanied by a profound failure of professional responsibility as described in paragraph 10.",
  "citation": "Article 16(6) and 16(10)",
  "gold_child_ids": "EU_376_2014_ART_16__C0007;EU_376_2014_ART_16__C0008;EU_376_2014_ART_16__C0016;EU_376_2014_ART_16__C0017;EU_376_2014_ART_16__C0018",
  "evidence": "EU_376_2014_ART_16__C0007 [Article 16(6)]: 6.Without prejudice to applicable national criminal law, Member States shall refrain from instituting proceedings in respect of unpremeditated or inadvertent infringements of the law which come to their attention only because they have been reported pursuant to Articles 4 and 5.\nEU_376_2014_ART_16__C0008 [Article 16(6)]: The first subparagraph shall not apply in the cases referred to in paragraph 10. Member States may retain or adopt measures to strengthen the protection of reporters or persons mentioned in occurrence reports. Member States may in particular apply this rule without the exceptions referred to in paragraph 10.\nEU_376_2014_ART_16__C0016 [Article 16(10)]: 10.The protection under paragraphs 6, 7 and 9 of this Article shall not apply to any of the following situations:\nEU_376_2014_ART_16__C0017 [Article 16(10)(a)]: (a)in cases of wilful misconduct;\nEU_376_2014_ART_16__C0018 [Article 16(10)(b)]: (b)where there has been a manifest, severe and serious disregard of an obvious risk and profound failure of professional responsibility to take such care as is evidently required in the circumstances, causing foreseeable damage to a person or property, or which seriously compromises the level of aviation safety."
 },
 {
  "qa_id": "QA_0287",
  "source_class": "ARTICLE",
  "question_type": "obligation",
  "difficulty": "hard",
  "review_reason": "exception_record",
  "split": "test",
  "question": "How do the Agency's review duty and Member States' notification duty apply to ERCS conversion procedures?",
  "reference_answer": "The Agency must regularly review the Annex conversion procedures to ensure their continuing relevance. When applicable, Member States must notify the Commission and the Agency when they use the manual procedure in point 2 of the Annex or other procedures referred to in Article 3(2).",
  "citation": "Article 5(1)-(2)",
  "gold_child_ids": "EU_2021_2082_ART_5__C0001;EU_2021_2082_ART_5__C0002",
  "evidence": "EU_2021_2082_ART_5__C0001 [Article 5(1)]: 1.The conversion procedures set out in the Annex shall be subject to regular review by the Agency to ensure its continuing relevance. The review may take account of the expertise of the NoA and relevant expert groups if established by the Agency.\nEU_2021_2082_ART_5__C0002 [Article 5(2)]: 2.When applicable, Member States shall notify to the Commission and the Agency the use of the manual conversion procedure set out in point 2 of the Annex and other conversion procedures referred to in Article 3(2) of this Regulation."
 },
 {
  "qa_id": "QA_0289",
  "source_class": "GM",
  "question_type": "scope",
  "difficulty": "hard",
  "review_reason": "stratified_unchanged_GM_development",
  "split": "development",
  "question": "What are the implications for reporting an occurrence if there is only one pilot on board an aircraft, and how does this relate to the definitions of crew members in Article 4(6)(a)?",
  "reference_answer": "If there is only one pilot on board, the provision stipulates that the cabin manager becomes the next crew member in the chain of command for reporting purposes. This means that the cabin manager is responsible for reporting if the pilot is unable to do so. The implication is that the reporting hierarchy changes based on the crew configuration, which must be clearly defined within the organization's safety management system.",
  "citation": "Article 4(6)(a)",
  "gold_child_ids": "GM_EU_376_2014_SEC_2_2__C0015;GM_EU_376_2014_SEC_2_2__C0013",
  "evidence": "GM_EU_376_2014_SEC_2_2__C0015 [GM 2.2]: Example: Any other crew member next in the chain of command in the context of a CAT operation on-board of a large aeroplane would be the co-pilot whereas in the case where there is only one pilot on board it would be the cabin manager.\nGM_EU_376_2014_SEC_2_2__C0013 [GM 2.2]: In addition, Article 4(6) (a) refers to ‘‘the pilot in command, or, in cases where the pilot in command is unable to report the occurrence, any other crew member next in the chain of command of an aircraft’’. Situations where the pilot would be unable to report is understood as referring to cases where the pilot would be unable to report because he would not be physically able to do so."
 },
 {
  "qa_id": "QA_0290",
  "source_class": "GM",
  "question_type": "obligation",
  "difficulty": "hard",
  "review_reason": "exception_record",
  "split": "development",
  "question": "How should an organisation address cases where the pilot in command cannot report an occurrence?",
  "reference_answer": "The organisation should cover and describe those cases in its safety management system, including which other crew member is next in the chain of command when the pilot is physically unable to report.",
  "citation": "GM 2.2; Article 4(6)(a)",
  "gold_child_ids": "GM_EU_376_2014_SEC_2_2__C0013;GM_EU_376_2014_SEC_2_2__C0014;GM_EU_376_2014_SEC_2_2__C0016",
  "evidence": "GM_EU_376_2014_SEC_2_2__C0013 [GM 2.2]: In addition, Article 4(6) (a) refers to ‘‘the pilot in command, or, in cases where the pilot in command is unable to report the occurrence, any other crew member next in the chain of command of an aircraft’’. Situations where the pilot would be unable to report is understood as referring to cases where the pilot would be unable to report because he would not be physically able to do so.\nGM_EU_376_2014_SEC_2_2__C0014 [GM 2.2]: The reference to ‘‘any other crew member next in the chain of command’’ intends to cover any configuration of the crew.\nGM_EU_376_2014_SEC_2_2__C0016 [GM 2.2]: These situations should be covered and described by organisations within their safety management system."
 },
 {
  "qa_id": "QA_0292",
  "source_class": "GM",
  "question_type": "exception",
  "difficulty": "hard",
  "review_reason": "exception_record",
  "split": "development",
  "question": "Which persons engaged in manufacturing are described as covered by Article 4(6)(b)?",
  "reference_answer": "The guidance covers persons under Member-State or EASA oversight who are directly involved in producing aeronautical items, verify compliance with applicable design data, and are responsible for investigations with the type-certificate or design-approval holder to identify whether deviations could lead to an unsafe condition.",
  "citation": "GM 2.2; Article 4(6)(b)",
  "gold_child_ids": "GM_EU_376_2014_SEC_2_2__C0018",
  "evidence": "GM_EU_376_2014_SEC_2_2__C0018 [GM 2.2]: Key principle Article 4(6)(b) is understood as covering persons engaged in manufacturing of an aircraft, or any equipment or part thereof under the oversight of a Member State or of EASA, who are directly involved in the production of aeronautical items, have the role to verify compliance with applicable design data and the responsibility to perform investigations with the holder of the type-certificate or design approval in order to identify if those deviations could lead to an unsafe condition."
 },
 {
  "qa_id": "QA_0293",
  "source_class": "GM",
  "question_type": "obligation",
  "difficulty": "hard",
  "review_reason": "exception_record",
  "split": "development",
  "question": "How should a production organisation and design-approval holder assess deviations from design data?",
  "reference_answer": "The production organisation must liaise with the design organisation, and the responsible person investigates with the Design Approval Holder whether identified deviations from design data could lead to an unsafe condition in the final certified product.",
  "citation": "GM 2.2; Article 4(6)(b)",
  "gold_child_ids": "GM_EU_376_2014_SEC_2_2__C0018;GM_EU_376_2014_SEC_2_2__C0019;GM_EU_376_2014_SEC_2_2__C0020",
  "evidence": "GM_EU_376_2014_SEC_2_2__C0018 [GM 2.2]: Key principle Article 4(6)(b) is understood as covering persons engaged in manufacturing of an aircraft, or any equipment or part thereof under the oversight of a Member State or of EASA, who are directly involved in the production of aeronautical items, have the role to verify compliance with applicable design data and the responsibility to perform investigations with the holder of the type-certificate or design approval in order to identify if those deviations could lead to an unsafe condition.\nGM_EU_376_2014_SEC_2_2__C0019 [GM 2.2]: This is aligned with occurrence reporting requirements in Commission Regulation (EU) No 748/2012, where the production organisation is required to liaise with the design organisation to confirm that the deviation in design data is actually an unsafe condition.\nGM_EU_376_2014_SEC_2_2__C0020 [GM 2.2]: Example: A person working in a production organisation being responsible of the investigation, together with the Design Approval Holder (DAH), to confirm if identified deviations of the manufactured product from design data could lead to an unsafe condition of the final certified product."
 },
 {
  "qa_id": "QA_0294",
  "source_class": "GM",
  "question_type": "scope",
  "difficulty": "hard",
  "review_reason": "exception_record",
  "split": "development",
  "question": "What criteria describe manufacturing personnel covered by Article 4(6)(b) in the guidance?",
  "reference_answer": "They are persons under Member-State or EASA oversight who are directly involved in producing aeronautical items, verify compliance with applicable design data, and are responsible for investigations with the type-certificate or design-approval holder to identify potentially unsafe deviations.",
  "citation": "GM 2.2; Article 4(6)(b)",
  "gold_child_ids": "GM_EU_376_2014_SEC_2_2__C0018",
  "evidence": "GM_EU_376_2014_SEC_2_2__C0018 [GM 2.2]: Key principle Article 4(6)(b) is understood as covering persons engaged in manufacturing of an aircraft, or any equipment or part thereof under the oversight of a Member State or of EASA, who are directly involved in the production of aeronautical items, have the role to verify compliance with applicable design data and the responsibility to perform investigations with the holder of the type-certificate or design approval in order to identify if those deviations could lead to an unsafe condition."
 }
];

// ---------------------------------------------------------------------------
function buildReviewForm() {
  var started = new Date().getTime();
  var props = PropertiesService.getScriptProperties();
  var nBlocks = Math.ceil(ROWS.length / BLOCK_SIZE);
  var form;

  if (!props.getProperty('FORM_ID')) {
    form = createShell();
    props.setProperty('FORM_ID', form.getId());
    props.setProperty('NEXT_BLOCK', '0');
    props.setProperty('PB_IDS', '[]');
    props.setProperty('GATE_IDS', '[]');
  } else {
    form = FormApp.openById(props.getProperty('FORM_ID'));
  }

  // links first, always, so a timeout can never cost you them
  Logger.log('==========================================================');
  Logger.log('FORM (send this link) : ' + form.getPublishedUrl());
  Logger.log('FORM (edit)           : ' + form.getEditUrl());
  if (props.getProperty('SS_ID')) {
    Logger.log('RESPONSE SHEET        : '
      + SpreadsheetApp.openById(props.getProperty('SS_ID')).getUrl());
  }
  Logger.log('==========================================================');

  var next  = parseInt(props.getProperty('NEXT_BLOCK'), 10);
  var pbIds = JSON.parse(props.getProperty('PB_IDS'));
  var gtIds = JSON.parse(props.getProperty('GATE_IDS'));

  while (next < nBlocks && (new Date().getTime() - started) < TIME_BUDGET_MS) {
    var slice = ROWS.slice(next * BLOCK_SIZE, (next + 1) * BLOCK_SIZE);

    var pb = form.addPageBreakItem()
      .setTitle('Bloc ' + (next + 1) + '/' + nBlocks + ' - Block ' + (next + 1) + ' of ' + nBlocks)
      .setHelpText('Fiches / Records: ' + slice[0].qa_id + ' -> ' + slice[slice.length - 1].qa_id);
    pbIds.push(pb.getId());

    for (var i = 0; i < slice.length; i++) addRecord(form, slice[i]);

    if (next < nBlocks - 1) {
      var gate = form.addMultipleChoiceItem()
        .setTitle('>>> Bloc ' + (next + 1) + ' termine - Continuer ? / Block ' + (next + 1) + ' done - Continue?')
        .setHelpText('FR - Si vous arretez maintenant vos reponses sont conservees : choisissez "envoyer".\n'
                   + 'EN - If you stop now your answers are kept: choose "submit".')
        .setRequired(true);
      gtIds.push(gate.getId());
    }

    next++;
    props.setProperty('NEXT_BLOCK', String(next));
    props.setProperty('PB_IDS', JSON.stringify(pbIds));
    props.setProperty('GATE_IDS', JSON.stringify(gtIds));
    Logger.log('block ' + next + '/' + nBlocks + ' added');
  }

  if (next < nBlocks) {
    Logger.log('----------------------------------------------------------');
    Logger.log('PARTIAL: ' + next + '/' + nBlocks + ' blocks built.');
    Logger.log('>>> RUN buildReviewForm AGAIN to continue. Nothing is lost.');
    Logger.log('----------------------------------------------------------');
    return;
  }

  if (props.getProperty('FINISHED') !== 'yes') {
    form.addPageBreakItem().setTitle('Merci / Thank you');
    form.addParagraphTextItem()
      .setTitle('Z1. Remarque generale (optionnel) / General remark (optional)')
      .setRequired(false);

    // wire the block gates now that every page exists
    for (var g = 0; g < gtIds.length; g++) {
      var gateItem = form.getItemById(gtIds[g]).asMultipleChoiceItem();
      var nextPage = form.getItemById(pbIds[g + 1]).asPageBreakItem();
      gateItem.setChoices([
        gateItem.createChoice('Continuer / Continue', nextPage),
        gateItem.createChoice('J\'ai termine, envoyer / I am done, submit',
                              FormApp.PageNavigationType.SUBMIT)
      ]);
    }
    props.setProperty('FINISHED', 'yes');
  }

  Logger.log('=========== BUILD COMPLETE - ' + ROWS.length + ' records ===========');
  Logger.log('Now open the form > Send > link settings and turn OFF');
  Logger.log('"Restrict to users in your organisation".');
}

// ---------------------------------------------------------------------------
function createShell() {
  var form = FormApp.create('PFE - Revue du benchmark / Benchmark review (Reg. (EU) 376/2014)');

  form.setDescription(
    'FR - Merci de votre aide. Chaque fiche contient une question, une reponse proposee, une citation, '
  + 'et le TEXTE REGLEMENTAIRE EXACT sur lequel la reponse est censee reposer. Votre tache : dire si la '
  + 'reponse est reellement soutenue par ce texte. Aucune recherche externe n\'est necessaire. '
  + 'Vous pouvez vous arreter apres n\'importe quel bloc : les reponses partielles sont utiles.\n\n'
  + 'EN - Thank you for helping. Each record contains a question, a proposed answer, a citation, and the '
  + 'EXACT REGULATORY TEXT the answer is supposed to rest on. Your task: say whether the answer is genuinely '
  + 'supported by that text. No external research needed. You may stop after any block: partial responses '
  + 'are useful.\n\n~2 min par fiche / per record.');

  form.setCollectEmail(false);
  form.setProgressBar(true);
  form.setAllowResponseEdits(true);
  form.setShowLinkToRespondAgain(false);

  form.addSectionHeaderItem()
    .setTitle('0. Vous / About you')
    .setHelpText('FR - Sert a documenter la qualification des evaluateurs dans le memoire.\n'
               + 'EN - Used to document reviewer qualification in the thesis.');

  form.addTextItem()
    .setTitle('R1. Nom ou role / Name or role')
    .setHelpText('FR - Nom, ou simplement votre fonction. EN - Name, or simply your function.')
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('R2. Experience dans l\'aviation / Aviation experience')
    .setChoiceValues(['Aucune / None', 'Moins de 2 ans / Under 2 years', '2-5 ans / 2-5 years',
                      '5-10 ans / 5-10 years', 'Plus de 10 ans / Over 10 years'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('R3. Familiarite avec le Reglement (UE) 376/2014 / Familiarity with Reg. (EU) 376/2014')
    .setChoiceValues(['Je travaille directement avec / I work with it directly',
                      'Je le connais / I know it',
                      'J\'en ai entendu parler / I have heard of it',
                      'Pas du tout / Not at all'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('R4. Langue de travail principale / Main working language')
    .setChoiceValues(['Francais / French', 'Anglais / English', 'Autre / Other'])
    .setRequired(false);

  var ss = SpreadsheetApp.create('PFE - Reponses revue benchmark / Benchmark review responses');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
  PropertiesService.getScriptProperties().setProperty('SS_ID', ss.getId());
  return form;
}

// ---------------------------------------------------------------------------
function addRecord(form, r) {
  var ev = (r.evidence && r.evidence.length)
    ? r.evidence
    : '(aucun extrait - fiche proposee a l\'exclusion / no evidence - record proposed for exclusion)';

  form.addSectionHeaderItem()
    .setTitle('--- ' + r.qa_id + ' ---')
    .setHelpText(
        'QUESTION\n' + r.question
      + '\n\nREPONSE PROPOSEE / PROPOSED ANSWER\n' + r.reference_answer
      + '\n\nCITATION PROPOSEE / PROPOSED CITATION\n' + (r.citation || '(aucune / none)')
      + '\n\nTEXTE REGLEMENTAIRE FOURNI / REGULATORY TEXT PROVIDED\n' + ev
      + '\n\n[' + r.source_class + ' | ' + r.question_type + ' | ' + r.difficulty + ']');

  form.addGridItem()
    .setTitle(r.qa_id + ' | C - Evaluation / Assessment')
    .setRows(['1. Question claire et non ambigue / Question clear and unambiguous',
              '2. Reponse soutenue par le texte / Answer supported by the text',
              '3. Citation correcte / Citation correct',
              '4. Extraits complets / Evidence complete'])
    .setColumns(['Oui / Yes', 'Partiellement / Partially', 'Non / No', 'Incertain / Unsure'])
    .setRequired(false);

  form.addMultipleChoiceItem()
    .setTitle(r.qa_id + ' | Q5 - Decision globale / Overall decision')
    .setChoiceValues(['Accepter / Accept',
                      'Accepter avec correction / Accept with correction',
                      'Rejeter / Reject',
                      'Je passe cette fiche / I skip this record'])
    .setRequired(false);

  form.addParagraphTextItem()
    .setTitle(r.qa_id + ' | Q6 - Commentaire (optionnel) / Comment (optional)')
    .setHelpText('FR - Si "correction" ou "rejeter", dites brievement pourquoi. '
               + 'EN - If "correction" or "reject", briefly say why.')
    .setRequired(false);
}

// ---------------------------------------------------------------------------
/** Clears saved progress so buildReviewForm starts a brand-new form. */
function resetReviewForm() {
  PropertiesService.getScriptProperties().deleteAllProperties();
  Logger.log('Progress cleared. Delete the old form in Drive, then run buildReviewForm.');
}

/** Prints the links again without building anything. */
function showLinks() {
  var props = PropertiesService.getScriptProperties();
  if (!props.getProperty('FORM_ID')) { Logger.log('No form built yet.'); return; }
  var form = FormApp.openById(props.getProperty('FORM_ID'));
  Logger.log('FORM  : ' + form.getPublishedUrl());
  Logger.log('EDIT  : ' + form.getEditUrl());
  Logger.log('SHEET : ' + SpreadsheetApp.openById(props.getProperty('SS_ID')).getUrl());
  Logger.log('Blocks built: ' + props.getProperty('NEXT_BLOCK')
             + ' | finished: ' + props.getProperty('FINISHED'));
}
