import os

# Mandatory
BACKEND_HOST = os.environ.get("BACKEND_HOST", "")

# Database
DB_HOST = os.environ.get("DB_HOST", "34.122.186.157")
DB_PORT = os.environ.get("DB_PORT", 5432)
DB_PASSWORD = os.environ.get("DB_PASSWORD", "mckinsey2023")
DB_NAME = os.environ.get("DB_NAME", "gpt_server_new")
DB_USER = os.environ.get("DB_USER", "postgres")

# Bot tokens
AI_GIRL_KEY = os.environ.get("AI_GIRL_TG_TOKEN", "")
WHAT_SHE_THINKS_KEY = os.environ.get("WHAT_SHE_THINKS_TG_TOKEN", "")
