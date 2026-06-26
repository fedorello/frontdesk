"""SaaS per-business config tables (telegram_bot, llm_config).

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-26

Idempotent (CREATE TABLE IF NOT EXISTS): a fresh database already has these from the
v1 schema; an existing one gets them here. See ADR-0008 / ADR-0009.
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_TELEGRAM_BOT = """
CREATE TABLE IF NOT EXISTS telegram_bot (
    business_id text PRIMARY KEY REFERENCES business(id),
    bot_token text NOT NULL,
    secret_token text NOT NULL,
    username text,
    webhook_set boolean NOT NULL DEFAULT false
)
"""

_LLM_CONFIG = """
CREATE TABLE IF NOT EXISTS llm_config (
    business_id text PRIMARY KEY REFERENCES business(id),
    mode text NOT NULL DEFAULT 'default',
    provider text,
    model text,
    base_url text,
    api_key_ciphertext text,
    api_key_hint text
)
"""


def upgrade() -> None:
    op.execute(_TELEGRAM_BOT)
    op.execute(_LLM_CONFIG)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS llm_config")
    op.execute("DROP TABLE IF EXISTS telegram_bot")
