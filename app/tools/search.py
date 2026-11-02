"""
Knowledge and Search Tool.
Answers domain questions directly from the indexed .md domain knowledge base.
"""
from app.tools.base import BaseTool, ToolResult
from app.knowledge.markdown_loader import domain_knowledge


class KnowledgeSearchTool(BaseTool):
    name = "knowledge_search"
    description = "Searches the domain knowledge base (.md file) for procedures, rules, support info, and facts."
    parameters_schema = {
        "query": {"type": "string", "description": "Search term or domain question"}
    }

    def execute(self, query: str = "", **kwargs) -> ToolResult:
        q_clean = query.strip()
        if not q_clean:
            return ToolResult(
                success=False,
                error="Empty search query",
                message="Please provide a question or topic to search.",
            )

        # Query domain knowledge from the markdown knowledge base
        res = domain_knowledge.query(q_clean)
        if res.found and res.top_section:
            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "section_title": res.top_section.title,
                    "section_content": res.top_section.content,
                    "summary": res.top_section.summary,
                    "score": res.score,
                },
                message=res.answer,
            )

        return ToolResult(
            success=True,
            data={"query": query, "found": False},
            message=res.answer,
        )
