"""Clinical knowledge base — the substance behind MedAgent's medical reasoning.

This package replaces "let the LLM hallucinate" with curated, evidence-based
content that the agent retrieves at runtime. Three buckets:

* ``chief_complaints/`` — YAML decision trees for the top primary-care
  presentations (fever, cough, headache, …). Each file is the clinical
  ground truth for one complaint: red flags, differentials, workup,
  treatments, escalation rules. Sourced from NICE CKS + WHO IMCI.
* ``formulary/`` — Egyptian drug formulary. OTC + common Rx with local
  brand names, dose by age/weight, contraindications.
* ``specialties/`` — pre-visit intake templates for B2B clinic workflow
  (GP, Pediatrics, OBGYN, ENT, Dermatology). Each defines the required
  intake fields and the structured questions the agent asks to fill them.

Everything here is data, not code. Adding a new chief complaint is dropping
a YAML file — no Python changes. That's the whole point: this is the
clinically-authored layer a real physician can edit without touching the
service code.
"""
