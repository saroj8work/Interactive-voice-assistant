"""
Configuration module for the Interactive Voice Assistant Agent.
Manages LLM model provider credentials, server settings, and runtime storage.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
NOTES_DIR = DATA_DIR / "notes"
AUDIO_TMP_DIR = DATA_DIR / "audio_tmp"
DOMAIN_KNOWLEDGE_FILE = DATA_DIR / "domain_knowledge.md"

NOTES_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_TMP_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseModel):
    app_name: str = "Interactive Voice Assistant Agent"
    version: str = "1.0.0"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")

    # LLM Model Configuration
    # Supported providers: 'gemini', 'groq', 'openai', 'anthropic', 'ollama'
    model_provider: str = os.getenv("MODEL_PROVIDER", "gemini").lower().strip()
    model_name: str = os.getenv("MODEL_NAME", "").strip()

    # Model Credentials
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Security & Voice Authorization Configuration
    admin_voice_passkey: str = os.getenv("ADMIN_VOICE_PASSKEY", "4291")
    require_admin_authorization: bool = os.getenv("REQUIRE_ADMIN_AUTHORIZATION", "true").lower() in ("true", "1", "yes")
    audit_signing_secret: str = os.getenv("AUDIT_SIGNING_SECRET", "eln_gxp_audit_secret_2026")

    # Paths
    base_dir: Path = BASE_DIR
    data_dir: Path = DATA_DIR
    notes_dir: Path = NOTES_DIR
    audio_tmp_dir: Path = AUDIO_TMP_DIR
    domain_knowledge_file: Path = Path(os.getenv("DOMAIN_KNOWLEDGE_FILE", str(DOMAIN_KNOWLEDGE_FILE)))

    def get_effective_model_name(self) -> str:
        """Returns the resolved model string based on provider."""
        if self.model_name:
            return self.model_name
        
        defaults = {
            "gemini": "gemini-3.5-flash",
            "groq": "llama-3.3-70b-versatile",
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-haiku-latest",
            "ollama": "llama3.2",
        }
        return defaults.get(self.model_provider, "gemini-3.5-flash")

    def is_configured(self) -> bool:
        """Checks if valid credentials exist for the selected provider."""
        p = self.model_provider
        if p == "gemini":
            return bool(self.gemini_api_key)
        elif p == "groq":
            return bool(self.groq_api_key)
        elif p == "openai":
            return bool(self.openai_api_key)
        elif p == "anthropic":
            return bool(self.anthropic_api_key)
        elif p == "ollama":
            return bool(self.ollama_base_url)
        return False

    def get_info(self) -> Dict[str, Any]:
        """Returns public model configuration metadata (keys masked)."""
        return {
            "model_provider": self.model_provider,
            "model_name": self.get_effective_model_name(),
            "configured": self.is_configured(),
            "has_gemini_key": bool(self.gemini_api_key),
            "has_groq_key": bool(self.groq_api_key),
            "has_openai_key": bool(self.openai_api_key),
            "has_anthropic_key": bool(self.anthropic_api_key),
            "ollama_base_url": self.ollama_base_url,
            "domain_knowledge_file": str(self.domain_knowledge_file),
        }


settings = Settings()
