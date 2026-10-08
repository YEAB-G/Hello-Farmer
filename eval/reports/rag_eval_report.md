# RAG Retrieval & Cross-Lingual Evaluation Report (eval/reports/rag_eval_report.md)

Generated: 2026-10-08 13:41:34

## Summary Metrics
- **Hit Rate @ 1**: 26.7%
- **Hit Rate @ 3**: 56.7%
- **Hit Rate @ 4**: 56.7%
- **Cross-Lingual Retrieval**: 60.0%
- **Source Tier 4 Enforcement**: Strictly Rejected (Passed)
- **Placeholder Set Status**: Flagged as `placeholder` tier (No doses, rates, or chemical recommendations permitted)

## Detailed Evaluation Breakdown
| Language | Topic | Query | Expected Doc | Top-3 Retrieved | Top Score | Hit@3 |
|---|---|---|---|---|---|---|
| am | DOC-001 | የጤፍ ሰብል ቅጠል ቢጫ ሲሆን ምን ማድረግ አለብኝ? | DOC-001 | DOC-001, DOC-004 | 0.08 | ✓ |
| en | DOC-001 | Teff yellow leaves in waterlogged soil | DOC-001 | DOC-002, DOC-001, DOC-004 | 0.09 | ✓ |
| om | DOC-001 | Baalli xaafii bishaan kuullamuun keelloo tahe | DOC-001 | DOC-003, DOC-004, DOC-005 | 0.02 | ✗ |
| am | DOC-001 | የጤፍ ማሳ ላይ ውሃ ሲተኛ የቅጠል መቀየር | DOC-001 | DOC-004, DOC-001, DOC-003 | 0.03 | ✓ |
| en | DOC-001 | Teff root zone moisture stress | DOC-001 | DOC-003, DOC-002 | 0.05 | ✗ |
| om | DOC-001 | Xaafii irratti bishaan dhangalaasuu | DOC-001 | DOC-003, DOC-005 | 0.05 | ✗ |
| am | DOC-002 | በበቆሎ ቅጠል ላይ ቡናማ ነጠብጣቦች ታይተዋል | DOC-002 | DOC-001, DOC-002, DOC-005 | 0.04 | ✓ |
| en | DOC-002 | Maize leaf blight symptoms during wet humid weather | DOC-002 | DOC-004, DOC-005 | 0.04 | ✗ |
| om | DOC-002 | Boqqoolloo irratti dhibeen baalaa maalidha? | DOC-002 | DOC-002, DOC-004 | 0.03 | ✓ |
| am | DOC-002 | በቆሎ ላይ ፈንገስ ሲከሰት ምልክቱ ምንድን ነው? | DOC-002 | DOC-002, DOC-003, DOC-001 | 0.05 | ✓ |
| en | DOC-002 | Elongated grayish spots on maize leaves | DOC-002 | DOC-002, DOC-004 | 0.04 | ✓ |
| om | DOC-002 | Mallattoo dhibee baala boqqoolloo | DOC-002 |  | 0.00 | ✗ |
| am | DOC-003 | የስንዴ ቢጫ ዋግ በሽታ ምልክቶች ምንድናቸው? | DOC-003 | DOC-003, DOC-001, DOC-002 | 0.04 | ✓ |
| en | DOC-003 | Wheat stripe rust linear orange pustules | DOC-003 | DOC-001, DOC-002, DOC-003 | 0.05 | ✓ |
| om | DOC-003 | Dhibeen waagii qamadii akkamitti beekama? | DOC-003 | DOC-002, DOC-004, DOC-005 | 0.07 | ✗ |
| am | DOC-003 | በስንዴ ቅጠል ላይ ቢጫ መስመሮች በደጋ አካባቢ | DOC-003 | DOC-004 | 0.03 | ✗ |
| en | DOC-003 | Highland wheat yellow rust detection | DOC-003 | DOC-002, DOC-005, DOC-001 | 0.09 | ✗ |
| om | DOC-003 | Qamadii irratti sarara keelloo | DOC-003 | DOC-003, DOC-001 | 0.07 | ✓ |
| am | DOC-004 | የጥቁር አፈር የውሃ ማቆር ችግርን እንዴት ማስተካከል ይቻላል? | DOC-004 | DOC-001, DOC-003 | 0.05 | ✗ |
| en | DOC-004 | Vertisol black clay soil drainage in Ethiopian highlands | DOC-004 | DOC-004, DOC-002, DOC-005 | 0.02 | ✓ |
| om | DOC-004 | Biyyeen kotichaa bishaan baay'ee yoo qabate | DOC-004 | DOC-002, DOC-004 | 0.04 | ✓ |
| am | DOC-004 | ወልካ አፈር ላይ የቦይ ማውጣት ዘዴ | DOC-004 | DOC-001, DOC-004, DOC-002 | 0.05 | ✓ |
| en | DOC-004 | Broadbed and furrow vertisol techniques | DOC-004 | DOC-003, DOC-002, DOC-005 | 0.07 | ✗ |
| om | DOC-004 | Bo'oo lolaa baasuu koticha | DOC-004 | DOC-001 | 0.05 | ✗ |
| am | DOC-005 | የግብርና ኬሚካል ሲረጭ ምን አይነት ጥንቃቄ ያስፈልጋል? | DOC-005 | DOC-002, DOC-005, DOC-001 | 0.06 | ✓ |
| en | DOC-005 | Safe pesticide application and protective equipment | DOC-005 | DOC-005, DOC-003, DOC-002 | 0.03 | ✓ |
| om | DOC-005 | Qoricha qonnaa yeroo fufan of eeggannoo | DOC-005 | DOC-004, DOC-002, DOC-005 | 0.04 | ✓ |
| am | DOC-005 | የፀረ ተባይ መመረዝ ሲያጋጥም ወዴት መሄድ አለበት? | DOC-005 | DOC-003, DOC-005 | 0.06 | ✓ |
| en | DOC-005 | Avoid spraying pesticide against wind direction | DOC-005 | DOC-003, DOC-001 | 0.03 | ✗ |
| om | DOC-005 | Kallattii qilleensaan qoricha fufuu dhiisuu | DOC-005 | DOC-002, DOC-004 | 0.04 | ✗ |
