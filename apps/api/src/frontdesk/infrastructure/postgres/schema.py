"""The database schema as ordered DDL statements.

One source of truth, used by both the Alembic migration and the integration-test
setup, so the migration and the tests can never drift.
"""

CREATE_STATEMENTS: tuple[str, ...] = (
    # GiST needs btree_gist to use `=` on the scalar resource_id in the
    # no-double-book exclusion constraint (see ADR-0004).
    "CREATE EXTENSION IF NOT EXISTS btree_gist",
    """
    CREATE TABLE business (
        id text PRIMARY KEY,
        name text NOT NULL,
        timezone text NOT NULL,
        lead_time_minutes integer NOT NULL DEFAULT 0,
        buffer_minutes integer NOT NULL DEFAULT 0,
        knowledge jsonb NOT NULL DEFAULT '[]',
        description text NOT NULL DEFAULT '',
        address text NOT NULL DEFAULT '',
        online boolean NOT NULL DEFAULT false,
        locale text NOT NULL DEFAULT 'en'
    )
    """,
    """
    CREATE TABLE channel_binding (
        channel text NOT NULL,
        address text NOT NULL,
        business_id text NOT NULL REFERENCES business(id),
        PRIMARY KEY (channel, address)
    )
    """,
    # Per-business Telegram bot (token + webhook secret are encrypted; see ADR-0009).
    """
    CREATE TABLE telegram_bot (
        business_id text PRIMARY KEY REFERENCES business(id),
        bot_token text NOT NULL,
        secret_token text NOT NULL,
        username text,
        webhook_set boolean NOT NULL DEFAULT false,
        last_update_id bigint NOT NULL DEFAULT 0
    )
    """,
    # Per-business LLM provider: the platform default, or the business's own key.
    """
    CREATE TABLE llm_config (
        business_id text PRIMARY KEY REFERENCES business(id),
        mode text NOT NULL DEFAULT 'default',
        provider text,
        model text,
        base_url text,
        api_key_ciphertext text,
        api_key_hint text
    )
    """,
    # Owner accounts: one account owns one business (its scope).
    """
    CREATE TABLE account (
        id text PRIMARY KEY,
        email text NOT NULL UNIQUE,
        password_hash text NOT NULL,
        business_id text REFERENCES business(id)
    )
    """,
    # Per-business daily usage of the managed-default LLM (cost control; ADR-0009).
    """
    CREATE TABLE usage_counter (
        business_id text NOT NULL REFERENCES business(id),
        day text NOT NULL,
        count integer NOT NULL DEFAULT 0,
        PRIMARY KEY (business_id, day)
    )
    """,
    """
    CREATE TABLE resource (
        id text PRIMARY KEY,
        business_id text NOT NULL REFERENCES business(id),
        name text NOT NULL,
        working_hours jsonb NOT NULL DEFAULT '[]'
    )
    """,
    """
    CREATE TABLE service (
        id text PRIMARY KEY,
        business_id text NOT NULL REFERENCES business(id),
        name text NOT NULL,
        duration_minutes integer NOT NULL,
        price_cents integer,
        currency text,
        resource_ids jsonb NOT NULL DEFAULT '[]',
        description text NOT NULL DEFAULT '',
        working_hours jsonb NOT NULL DEFAULT '[]',
        max_advance_days integer NOT NULL DEFAULT 30
    )
    """,
    """
    CREATE TABLE customer (
        id text PRIMARY KEY,
        business_id text NOT NULL REFERENCES business(id),
        channel text NOT NULL,
        address text NOT NULL,
        name text,
        language text,
        UNIQUE (business_id, channel, address)
    )
    """,
    """
    CREATE TABLE message (
        id bigserial PRIMARY KEY,
        business_id text NOT NULL,
        customer_id text NOT NULL REFERENCES customer(id),
        role text NOT NULL,
        body text NOT NULL,
        at timestamptz NOT NULL,
        tool_call_id text
    )
    """,
    """
    CREATE TABLE appointment (
        id text PRIMARY KEY,
        business_id text NOT NULL REFERENCES business(id),
        service_id text NOT NULL,
        resource_id text NOT NULL,
        customer_id text NOT NULL,
        starts_at timestamptz NOT NULL,
        ends_at timestamptz NOT NULL,
        status text NOT NULL DEFAULT 'pending',
        CONSTRAINT no_double_book EXCLUDE USING gist (
            resource_id WITH =, tstzrange(starts_at, ends_at) WITH &&
        ) WHERE (status <> 'cancelled')
    )
    """,
    """
    CREATE TABLE reminder (
        id text PRIMARY KEY,
        business_id text NOT NULL,
        appointment_id text NOT NULL REFERENCES appointment(id),
        due_at timestamptz NOT NULL,
        kind text NOT NULL,
        status text NOT NULL DEFAULT 'pending'
    )
    """,
    "CREATE INDEX reminder_due ON reminder (status, due_at)",
)

DROP_STATEMENTS: tuple[str, ...] = tuple(
    f"DROP TABLE IF EXISTS {table} CASCADE"
    for table in (
        "reminder",
        "appointment",
        "message",
        "customer",
        "service",
        "resource",
        "usage_counter",
        "account",
        "llm_config",
        "telegram_bot",
        "channel_binding",
        "business",
    )
)
