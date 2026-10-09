# Agricultural Knowledge Base Sources (knowledge_base/SOURCES.md)

This document tracks all agricultural reference materials ingested into Hello Farmer, categorized by verified source tier.

---

## Source Tier Taxonomy

| Tier | Source Type | Examples & Guidelines | Permitted Agronomic Advice |
|---|---|---|---|
| **Tier 1** | Official Ethiopian Government & National Research | Ministry of Agriculture (MoA), Ethiopian Institute of Agricultural Research (EIAR), Regional Bureaus of Agriculture | **Primary authority**. Only tier authorized for specific doses, application rates, spray schedules, or chemical recommendations. |
| **Tier 2** | International Agricultural Research Bodies | FAO, CGIAR (CIMMYT, ICRISAT, ILRI, IFPRI) with Ethiopia-specific publications | General agronomic practice, pest & disease identification. Doses only if verified against Ethiopian regulations. |
| **Tier 3** | Peer-Reviewed Research & University Extension | Haramaya University, Hawassa University, academic journals | Agronomic context, biological mechanisms, background explanation. **Never** the basis for dosage or chemical recommendations. |
| **Tier 4** | Unvetted Sources | Blogs, social media, internet forums, unverified AI summaries | **STRICTLY PROHIBITED**. Ingestion pipeline rejects Tier 4 materials. |
| **Placeholder** | Synthetic Evaluation Notes | Internal non-numeric benchmark notes | Clearly labeled non-guidance. **Contains zero numbers, rates, or chemical names**. |

---

## 1. Placeholder Evaluation Set (Initial Scaffold)

> [!CAUTION]
> **WARNING: NON-AGRONOMIC PLACEHOLDER DATA ONLY**  
> The documents below are synthetic non-numeric notes created exclusively for system testing, cross-lingual retrieval verification, and fallback guardrail testing. They do NOT contain dosage rates, chemical recommendations, spray intervals, or yield numbers.

1. **DOC-001: Teff Growth Stages and Moisture Sensitivity (Placeholder)**
   - **Publisher**: Hello Farmer Evaluation Team (Synthetic)
   - **Year**: 2026
   - **Language**: Amharic / English
   - **Tier**: `placeholder`
   - **Topics**: Teff, moisture stress, waterlogging symptoms.

2. **DOC-002: Maize Leaf Blight and Rust Symptom Identification (Placeholder)**
   - **Publisher**: Hello Farmer Evaluation Team (Synthetic)
   - **Year**: 2026
   - **Language**: Afaan Oromo / English
   - **Tier**: `placeholder`
   - **Topics**: Maize, fungal leaf symptoms, visual inspection.

3. **DOC-003: Wheat Yellow Rust General Overview (Placeholder)**
   - **Publisher**: Hello Farmer Evaluation Team (Synthetic)
   - **Year**: 2026
   - **Language**: Amharic / English
   - **Tier**: `placeholder`
   - **Topics**: Wheat, stripe rust, early sign detection.

4. **DOC-004: Soil Drainage Practices for Ethiopian Vertisols (Placeholder)**
   - **Publisher**: Hello Farmer Evaluation Team (Synthetic)
   - **Year**: 2026
   - **Language**: Afaan Oromo / English
   - **Tier**: `placeholder`
   - **Topics**: Heavy black clay soils, drainage furrow concepts.

5. **DOC-005: Safe Pesticide Handling Principles and DA Consultation (Placeholder)**
   - **Publisher**: Hello Farmer Evaluation Team (Synthetic)
   - **Year**: 2026
   - **Language**: Amharic / English
   - **Tier**: `placeholder`
   - **Topics**: Safety equipment, pesticide label verification, referral to development agents.

---

## 2. Ingested Official Documents (Tier 1 & 2)

1. **DOC-MOA-001: Technical Manual for Integrated Soil Fertility Management (ISFM)**
   - **Publisher**: Ministry of Agriculture (MoA), Federal Democratic Republic of Ethiopia
   - **Tier**: `Tier 1` (National Extension Guideline)
   - **Topics**: Soil fertility replenishment, composting, biochar, mineral fertilizer combinations, crop rotation, soil acidity and liming.
   - **File**: `knowledge_base/raw/moa_isfm_technical_manual.md`

2. **DOC-MOA-002: Field Guide for Extension Agents on Integrated Soil Fertility Management**
   - **Publisher**: Ministry of Agriculture (MoA), Federal Democratic Republic of Ethiopia
   - **Tier**: `Tier 1` (Extension Field Guide)
   - **Topics**: Practical agronomic practices for smallholders, soil testing, vermicomposting, balanced nutrient application.
   - **File**: `knowledge_base/raw/moa_isfm_field_guide.md`

3. **DOC-MOA-003: National Fertilizer Blending and NP Strategy Manual**
   - **Publisher**: Ministry of Agriculture (MoA), Federal Democratic Republic of Ethiopia
   - **Tier**: `Tier 1` (Strategy & Policy Guideline)
   - **Topics**: NPS and urea fertilization ratios, targeted micro-nutrients (Zn, B), balanced fertilization for teff, wheat, and maize.
   - **File**: `knowledge_base/raw/moa_np_fertilizer_strategy.md`

4. **DOC-MOA-004: Cattle Urine Collection, Storage, and Agronomic Use Manual**
   - **Publisher**: Ministry of Agriculture (MoA), Federal Democratic Republic of Ethiopia
   - **Tier**: `Tier 1` (Practical Organic Agriculture Guide)
   - **Topics**: Liquid organic bio-fertilizer, cattle shed floor preparation, storage safety, dilution ratios, and foliar spray application.
   - **File**: `knowledge_base/raw/moa_cattle_urine_manual.md`

