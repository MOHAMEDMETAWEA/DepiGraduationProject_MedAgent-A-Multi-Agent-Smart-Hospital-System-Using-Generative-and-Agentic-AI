# MedAgent — AI Pipeline

> Documents the MedAgent AI architecture: agent loop, tools, RAG, and LLM integration.

## Overview

MedAgent uses a ReAct-style agent architecture with tool calling, RAG-based knowledge retrieval, and a multi-stage safety verification pipeline. The system supports Arabic and English (including code-switching).

## Agent Loop (ReAct)

```
function respond(user_message, conversation_history):
    1. Pre-flight checks
       - Detect language (Arabic/English/Franco)
       - Normalize Arabic text
       - Scrub PII from message
       - Check emergency red-flag keywords (fast path)

    2. Red-Flag Fast Path
       - If emergency keywords detected → return immediate emergency response
       - Bypasses LLM entirely for life-threatening situations

    3. Build Prompt
       - Load system prompt (language-specific, branch-specific)
       - Include conversation history
       - Attach tool specifications (names, descriptions, schemas)

    4. Agent Loop (max 5 iterations)
       - LLM responds with either:
         a) Final answer → proceed to step 5
         b) Tool call → execute tool, append result, continue loop

    5. Safety Verification
       - Run post-LLM hallucination detector
       - Calibrate uncertainty
       - Check for forbidden phrases

    6. Format & Stream Response
       - Format final response with citations
       - Stream tokens via SSE
       - Persist message and safety assessment
```

## Language Support

### Language Detection

The `ai/nlp/language.py` module detects:
- **Arabic** (Unicode Arabic script range)
- **English** (Latin script)
- **Franco** (Arabic written with Latin + digits: 7=ح, 3=ع, etc.)

### Arabic Normalization

- Normalizes Alef variants (أ إ آ → ا)
- Normalizes Yeh variants (ي ى → ي)
- Normalizes Teh Marbuta (ة → ه)
- Removes diacritics (Tashkeel)
- Handles code-switched messages (AR+EN in same text)

## System Prompts

System prompts are language-specific and branch-aware:

| Prompt File | Language | Context |
|---|---|---|
| `system_ar.txt` | Arabic | General medical triage |
| `system_en.txt` | English | General medical triage |
| `system_ar_pediatric.txt` | Arabic | Pediatric patients (< 18) |
| `system_en_pediatric.txt` | English | Pediatric patients |
| `system_ar_pregnancy.txt` | Arabic | Pregnant patients |
| `system_en_pregnancy.txt` | English | Pregnant patients |

## Tool System

### Architecture

Tools follow a pluggable architecture using the `Tool` abstract base class. The `ToolRegistry` manages tool registration and execution.

```python
class Tool(ABC):
    name: str
    description: str
    input_schema: dict  # JSON Schema for parameters

    async def run(self, **kwargs) -> ToolResult
```

### Core MVP Tools

| Tool | Purpose | Input | Output |
|---|---|---|---|
| `retrieve_medical_knowledge` | RAG search over knowledge base | query, language, top_k | List of KB chunks with sources |
| `score_triage` | Manchester Triage Scale assessment | symptoms, age, comorbidities | Level, score, reasoning |
| `detect_red_flags` | Emergency keyword detection | text, language | Flag list, severity |
| `summarize_for_doctor` | Generate handoff summary | conversation_id | Structured markdown summary |
| `analyze_vision` | Preliminary image triage | image_b64, kind, context | Findings, urgency, confidence |
| `format_soap` | SOAP note formatting | conversation data | Structured SOAP note |

### Specialized Clinical Tools

| Tool | Purpose | Context |
|---|---|---|
| `check_medication_interactions` | Drug-drug + allergy + dose safety | All patients on medication |
| `screen_mental_health` | PHQ-9 / GAD-7 screening | When mental health symptoms mentioned |
| `assess_pediatric_safety` | Age-aware safety gate | Patients < 18 |
| `assess_pregnancy_safety` | OB red flags + pregnancy category | Pregnant patients |
| `tot_differential_diagnosis` | Tree-of-Thought reasoning | Complex cases with uncertainty |
| `verify_no_hallucination` | Clinical claim verification | Post-LLM (Stage 3 safety) |
| `calibrate_uncertainty` | Confidence calibration | Post-LLM (Stage 3 safety) |

## Retrieval-Augmented Generation (RAG)

### Knowledge Base

The knowledge base is built from curated medical sources:
- WHO guidelines
- MedlinePlus
- Peer-reviewed medical Q&A
- Standardized clinical guidelines

### Pipeline

```
Source Documents
    ↓ chunking (tiktoken-based)
Text Chunks
    ↓ embedding (multilingual-e5-large, 1024-dim)
Vector Embeddings
    ↓ upsert (pgvector)
Vector Store
    ↓ query → retrieve top-k → rerank (bge-reranker-v2-m3)
Relevant Chunks with Scores
```

### Components

| Component | Technology | Details |
|---|---|---|
| Chunker | Custom + tiktoken | Splits text by semantic boundaries, max 512 tokens |
| Embeddings | `intfloat/multilingual-e5-large` | 1024 dimensions, multilingual |
| Vector Store | pgvector (PostgreSQL) | IVF-Flat index, cosine similarity |
| Reranker | `BAAI/bge-reranker-v2-m3` | Cross-encoder, multilingual |

## LLM Integration

### Provider Architecture

The `LLMProvider` abstract base class enables swapping LLM backends:

```python
class LLMProvider(ABC):
    async def generate(self, messages, tools, stream=True) -> AsyncGenerator
    async def generate_sync(self, messages, tools) -> LLMResponse
```

### Supported Providers

| Provider | Class | API Format |
|---|---|---|
| OpenRouter | `OpenAICompatProvider` | OpenAI-compatible |
| Groq | `OpenAICompatProvider` | OpenAI-compatible |
| Gemini | `OpenAICompatProvider` | OpenAI-compatible |
| HuggingFace | `HFInferenceProvider` | HF Inference API |
| Vision Models | `VisionProvider` | Specialized image analysis |

### Model Selection

Configured via environment variables:

```bash
LLM_PROVIDER=openrouter          # Provider selection
LLM_MODEL=qwen/qwen-2.5-7b-instruct  # Model ID
LLM_BASE_URL=https://openrouter.ai/api/v1  # API base URL
LLM_API_KEY=sk-or-...            # API key
```

### Streaming (SSE)

AI responses are streamed to the frontend via Server-Sent Events:

```
data: {"type": "token", "content": "Based on your symptoms..."}

data: {"type": "tool_start", "name": "retrieve_medical_knowledge", "input": {...}}

data: {"type": "tool_result", "name": "retrieve_medical_knowledge", "output": {...}}

data: {"type": "citation", "source": "WHO Guidelines 2024", "title": "..."}

data: {"type": "safety", "hallucination_score": 0.03, "uncertainty": "low"}

data: {"type": "triage", "level": "routine", "score": 25, "reasoning": "..."}

data: {"type": "done", "message_id": "uuid"}
```

### Tree-of-Thought (ToT) Mode

For complex differential diagnosis under uncertainty, the agent can switch to ToT mode:

1. Generate multiple diagnostic hypotheses
2. For each hypothesis, search knowledge base for supporting/refuting evidence
3. Score each path using confidence-weighted evidence
4. Return ranked differential with evidence trails

## MLflow Integration

Experiment tracking via MLflow:

- Agent call metrics (latency, tokens, tool usage)
- Safety metrics (hallucination rate, citation rate)
- Triage accuracy benchmarks
- Embedding quality metrics

## Model Fine-Tuning Pipeline

Located in `notebooks/` and `scripts/`:

1. **Data preparation:** Medical dialogue synthesis, knowledge base PDF processing
2. **Fine-tuning:** LoRA on Qwen2.5-7B using SFTTrainer
3. **Evaluation:** BLEU, ROUGE, BERTScore, triage accuracy, hallucination rate
4. **Deployment:** LoRA adapters uploaded to HuggingFace Hub
