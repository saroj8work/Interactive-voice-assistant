"""
Unit tests for Markdown Domain Knowledge Ingestion and Search.
"""
import tempfile
from pathlib import Path
from app.knowledge.markdown_loader import MarkdownDomainKnowledge
from app.agent.conversational import conversational_agent
from app.agent.llm_client import llm_client

SAMPLE_MD = """# Company Knowledge Base

## Support Hours
Our customer support team is available Monday through Friday from 8 AM to 5 PM EST.

## Refund Policy
Customers are eligible for a full refund within 30 days of purchase. Products must be undamaged.

## Smart Lighting
Living room lights support presets: Movie Night (20%), Reading (70%), and Full Bright (100%).
"""


def test_markdown_parsing():
    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
        f.write(SAMPLE_MD)
        tmp_path = Path(f.name)

    try:
        kb = MarkdownDomainKnowledge(file_path=tmp_path)
        assert len(kb.sections) == 3
        titles = [s.title for s in kb.sections]
        assert "Support Hours" in titles
        assert "Refund Policy" in titles
        assert "Smart Lighting" in titles
    finally:
        tmp_path.unlink(missing_ok=True)


def test_markdown_query_refund():
    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
        f.write(SAMPLE_MD)
        tmp_path = Path(f.name)

    try:
        kb = MarkdownDomainKnowledge(file_path=tmp_path)
        res = kb.query("What is the refund policy?")
        assert res.found is True
        assert res.top_section.title == "Refund Policy"
        assert "30 days" in res.top_section.content
    finally:
        tmp_path.unlink(missing_ok=True)


def test_conversational_agent_domain_knowledge():
    llm_client.set_mock_responses([
        {
            "thought": "User asks for support hours. Search domain knowledge base.",
            "intent": "web_search_knowledge",
            "action_required": True,
            "planned_tools": [
                {"tool_name": "knowledge_search", "action_description": "Search domain knowledge", "parameters": {"query": "support hours"}}
            ],
            "spoken_reply": "Our support team is available Monday to Friday from 9 AM to 6 PM EST.",
        }
    ])

    res = conversational_agent.chat(
        "What are your support hours?",
        session_id="kb_test_sess",
        generate_audio=False,
    )
    assert res.action_identified is True
    assert "support" in res.assistant_reply.lower() or "hours" in res.assistant_reply.lower()
