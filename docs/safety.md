# MedAgent — Safety Pipeline

> Documents the multi-stage safety architecture that ensures MedAgent never provides unsafe medical advice.

## Safety Philosophy

MedAgent operates under these principles:

1. **Never diagnose** — provides triage assessment and differential possibilities, not definitive diagnoses
2. **Always cite** — every clinical claim must reference a retrieved source
3. **Escalate emergencies** — red-flag symptoms trigger immediate ER referral, bypassing AI
4. **Defer to physicians** — final clinical judgment always rests with a licensed doctor
5. **Audit everything** — every state-changing operation is logged in a hash-chained audit trail

## Multi-Stage Safety Pipeline

```
User Input
    │
    ▼
┌──────────────────────────────────────────────┐
│ Stage 1: Pre-LLM Red-Flag Fast Path         │
│ - Emergency keyword detection (AR + EN)      │
│ - Pattern matching for life-threatening      │
│   symptoms (chest pain + radiating, etc.)    │
│ - Bypasses LLM entirely                      │
│ - Returns immediate ER guidance              │
└──────────────────────────────────────────────┘
    │ (if no emergency)
    ▼
┌──────────────────────────────────────────────┐
│ Stage 2: In-LLM Safety Rules                │
│ - System prompt enforces:                    │
│   "You are NOT a doctor"                     │
│   "Never provide a final diagnosis"          │
│   "Never prescribe medication"               │
│   "Always cite your sources"                 │
│   "For emergencies, redirect to ER"          │
│ - Branch-specific safety rules               │
│   (pediatric, pregnancy)                     │
└──────────────────────────────────────────────┘
    │ (post-generation)
    ▼
┌──────────────────────────────────────────────┐
│ Stage 3: Post-LLM Safety Gate               │
│                                              │
│ 3a. Hallucination Detection                  │
│     - Compare every clinical claim against   │
│       retrieved sources                      │
│     - Flag unsupported claims                │
│     - Score: 0.0 (fully grounded) to         │
│       1.0 (fully hallucinated)               │
│                                              │
│ 3b. Citation Completeness Check              │
│     - Ratio of cited claims to total claims  │
│     - Red-flag if < 50% cited                │
│                                              │
│ 3c. Forbidden Phrase Detection               │
│     - Pattern match: "you have [disease]"     │
│     - Pattern match: "take [medication]"      │
│     - Pattern match: definitive diagnosis     │
│     - Auto-rewrite to safe phrasing           │
│                                              │
│ 3d. Uncertainty Calibration                  │
│     - Per-claim confidence assessment        │
│     - Band: high / medium / low              │
│     - Low-confidence claims are flagged      │
│     - Users informed of uncertainty           │
│                                              │
│ 3e. Triage Consistency Check                 │
│     - Red-flags must match triage level      │
│     - Emergency-level flags with "routine"   │
│       triage = inconsistency, flagged        │
└──────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────┐
│ Stage 4: Audit & Monitoring                  │
│ - Hash-chained audit log (tamper-evident)    │
│ - Safety statistics dashboard                │
│ - Admin safety incident review               │
│ - Prometheus metrics                         │
└──────────────────────────────────────────────┘
```

## Stage 1: Red-Flag Fast Path

### Emergency Keywords

Defined in `ai/safety/red_flags_keywords.yaml`. Categories:

| Category | Arabic Examples | English Examples |
|---|---|---|
| Cardiac | ألم في الصدر, ذبحة صدرية | chest pain, heart attack, crushing pain |
| Neurological | تنميل نصف الجسم, صعوبة في الكلام | stroke, facial droop, slurred speech |
| Respiratory | صعوبة شديدة في التنفس, اختناق | can't breathe, choking, severe shortness of breath |
| Trauma | نزيف حاد, كسر مفتوح | severe bleeding, head injury, loss of consciousness |
| Allergic | تورم الوجه, صدمة حساسية | anaphylaxis, throat swelling, severe allergic |
| Psychiatric | أفكار انتحارية, إيذاء النفس | suicidal, want to die, self-harm |

### Emergency Response

When a red-flag keyword is detected:
1. Agent loop is completely bypassed
2. Immediate emergency response is returned
3. Patient is directed to nearest ER or ambulance (123 in Egypt)
4. Conversation is flagged for safety review
5. All clinical assessment is skipped

## Stage 3: Post-LLM Safety Gate

Implementation: `ai/safety/post_llm_gate.py`

### Hallucination Detection (3a)

Uses a separate verifier model (or the same model with a verification prompt) to:
1. Extract all clinical claims from the generated response
2. For each claim, compare against retrieved evidence
3. Score each claim: 0 = fully supported, 1 = no support found
4. Calculate overall hallucination score

### Forbidden Phrase Rewriting (3c)

Patterns that trigger automatic rewriting:

| Forbidden | Rewritten To |
|---|---|
| "You have [disease]" | "Your symptoms are consistent with [disease], but only a doctor can diagnose" |
| "Take [medication]" | "A doctor may consider [medication] if appropriate" |
| "You need surgery" | "A surgical consultation may be warranted" |
| "This is definitely [condition]" | "[Condition] is one possibility among several" |

## Data Protection

### PHI Encryption

Personally identifiable health information is encrypted at rest:

- **Algorithm:** AES-256 via Fernet (`cryptography` library)
- **Scope:** Message content, vision analysis, patient profile data
- **Toggle:** `PHI_ENCRYPTION_ENABLED` environment variable
- **Key:** `DATA_ENCRYPTION_KEY` (required in production)

### PII Scrubbing

Before messages reach the LLM:
- Email addresses → `[email]`
- Phone numbers → `[phone]`
- National IDs → `[id]`
- Names (if detected) → `[name]`

Implementation: `ai/agent/pii.py`

## Audit Trail

### Hash-Chained Audit Log (`common/audit_chain.py`)

Every state-changing operation is logged:

```
log_n = {
    sequence: n,
    user_id: ...,
    action: "create_conversation",
    resource_type: "conversation",
    resource_id: ...,
    details: {...},
    ip_address: ...,
    user_agent: ...,
    previous_hash: SHA256(log_{n-1}),
    current_hash: SHA256(previous_hash || canonical(log_n))
}
```

### Tamper Detection

The audit chain can be verified via `GET /admin/audit-verify`:
1. Walks the entire chain from genesis record
2. Recalculates each hash
3. Reports the first sequence where hash mismatches
4. Any tampering is immediately detectable

### Audit Log Fields

| Field | Description |
|---|---|
| `id` | UUID primary key |
| `sequence` | Monotonically increasing serial |
| `user_id` | Actor who performed the action |
| `action` | e.g., login, create_conversation, update_profile |
| `resource_type` | e.g., user, conversation, handoff |
| `resource_id` | UUID of affected resource |
| `details` | JSONB with action-specific metadata |
| `ip_address` | Client IP |
| `user_agent` | Client user agent |
| `previous_hash` | SHA-256 of previous record |
| `current_hash` | SHA-256 of this record |

## Safety Monitoring Dashboard

Available at `/admin/safety-stats` (admin only):

| Metric | Description |
|---|---|
| `hallucination_rate` | Percentage of responses with hallucination score > 0.3 |
| `citation_rate` | Average citation completeness across all responses |
| `uncertainty_distribution` | Breakdown: {high: N, medium: N, low: N} |
| `triage_inconsistencies` | Count of triage/symptom mismatches |
| `forbidden_phrase_rewrites_total` | Total forbidden phrases caught and rewritten |
| `flagged_conversations` | Conversations flagged for human review |

## Incident Response

When a safety incident is detected:

1. Conversation status → `flagged_for_review`
2. Incident appears in admin safety dashboard
3. Admin can review full conversation
4. Admin can verify hallucination source claims
5. Admin can take corrective action (disable user, escalate)
