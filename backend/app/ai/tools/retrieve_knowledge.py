"""Tool: retrieve_medical_knowledge — RAG search for the agent."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.ai.agent.base import Tool
from app.ai.retrieval.retriever import Retriever

# class RetrieverInput(BaseModel):
#     """Input schema for medical knowledge retrieval."""


#     query: str = Field(
#         min_length=1,
#         description="The medical question to search for in the knowledge base",
#     )
#     language: str = Field(
#         default="en",
#         pattern="^(ar|en)$",
#         description="Language filter: 'ar' or 'en'",
#     )
#     top_k: int = Field(
#         default=5,
#         ge=1,
#         le=20,
#         description="Number of top results to return (1-20)",
#     )
# ------------------------
class RetrieverInput(BaseModel):
    """Input schema for medical knowledge retrieval."""

    query: Any = Field(
        default="",
        description="The medical question to search for in the knowledge base",
    )
    language: Any = Field(
        default="en",
        description="Language filter: 'ar' or 'en'",
    )
    top_k: Any = Field(
        default=5,
        description="Number of top results to return (1-20)",
    )

    # 🟢 فلتر جملة البحث (يمنع الـ null ويحول القوائم لنص)
    @field_validator("query", mode="before")
    @classmethod
    def force_query_string(cls, v):
        if v is None or str(v).lower() == "null":
            return ""
        if isinstance(v, list):
            return " ".join([str(item) for item in v])
        return str(v).strip()

    # 🟢 فلتر اللغة (ذكي: لو لقى أي حاجة تدل على العربي بيقلبها ar، غير كده en)
    @field_validator("language", mode="before")
    @classmethod
    def force_language(cls, v):
        if v is None or str(v).lower() == "null":
            return "en"
        val_str = str(v).lower().strip()
        if "ar" in val_str or "عرب" in val_str:
            return "ar"
        return "en"

    # 🟢 فلتر العدد (يمنع الكراش لو الموديل بعت نص، ويحجم الرقم بين 1 و 20)
    @field_validator("top_k", mode="before")
    @classmethod
    def force_top_k(cls, v):
        if v is None or str(v).lower() == "null":
            return 5
        try:
            val = int(v)
            # يحجم الرقم عشان ميزيدش عن 20 وميقلش عن 1
            return max(1, min(20, val))
        except (ValueError, TypeError):
            return 5


class RetrieveKnowledgeTool(Tool):
    """Searches the medical knowledge base and returns top chunks with citations."""

    def __init__(self, retriever: Retriever):
        self._retriever = retriever

    @property
    def name(self) -> str:
        return "retrieve_medical_knowledge"

    @property
    def description(self) -> str:
        return (
            "Search the medical knowledge base for evidence-based guidelines, "
            "clinical information, and triage protocols. Returns relevant text "
            "chunks with source citations and URLs."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return RetrieverInput

    async def run(self, input_data: BaseModel) -> dict[str, Any]:

        if not isinstance(input_data, RetrieverInput):
            raise TypeError(f"Expected RetrieverInput, got {type(input_data)}")

        results = await self._retriever.search(
            query=input_data.query,
            language=input_data.language,
            top_k=input_data.top_k,
        )

        chunks = []
        for r in results:
            chunks.append(
                {
                    "source": r["source"],
                    "title": r.get("section_title", ""),
                    "url": r.get("source_url", ""),
                    "content_excerpt": r["content"][:300],
                    "similarity": round(r["similarity"], 3),
                }
            )

        return {
            "query": input_data.query,
            "total_results": len(chunks),
            "chunks": chunks,
        }
