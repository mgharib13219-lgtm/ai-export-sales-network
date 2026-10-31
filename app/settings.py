import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv('APP_NAME', 'AI Export Sales Network')
    admin_token: str = os.getenv('ADMIN_TOKEN', '')
    agent_cron_token: str = os.getenv('AGENT_CRON_TOKEN', '')
    agent_approver_token: str = os.getenv('AGENT_APPROVER_TOKEN', '')
    environment: str = os.getenv('ENVIRONMENT', 'development')
    app_version: str = os.getenv('APP_VERSION', '1.1.0')
    ai_provider: str = os.getenv('AI_PROVIDER', 'ensemble')
    ai_api_key: str = os.getenv('AI_API_KEY', '')
    anthropic_api_key: str = os.getenv('ANTHROPIC_API_KEY', '')
    anthropic_model: str = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-haiku-latest')
    gemini_api_key: str = os.getenv('GEMINI_API_KEY', '')
    gemini_model: str = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    ai_base_url: str = os.getenv('AI_BASE_URL', '')
    ai_model: str = os.getenv('AI_MODEL', 'gpt-4.1-mini')
    ai_web_search: bool = os.getenv('AI_WEB_SEARCH', 'true').lower() == 'true'
    search_provider: str = os.getenv('SEARCH_PROVIDER', 'serpapi')
    search_api_key: str = os.getenv('SEARCH_API_KEY', '')
    search_base_url: str = os.getenv('SEARCH_BASE_URL', '')
    email_provider: str = os.getenv('EMAIL_PROVIDER', 'none')
    email_api_key: str = os.getenv('EMAIL_API_KEY', '')
    database_url: str = os.getenv('DATABASE_URL', '')
    smtp_host: str = os.getenv('SMTP_HOST', '')
    smtp_port: int = int(os.getenv('SMTP_PORT', '587'))
    smtp_user: str = os.getenv('SMTP_USER', '')
    smtp_password: str = os.getenv('SMTP_PASSWORD', '')
    repeat_protection_days: int = int(os.getenv('REPEAT_PROTECTION_DAYS', '1095'))

settings = Settings()
