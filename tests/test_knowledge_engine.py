from datetime import UTC, datetime
from pathlib import Path
import os

import pytest

from app.knowledge.engine import TenantKnowledgeEngine
from app.tenants.loader import load_tenant_config


@pytest.fixture
def tenant_config():
    return load_tenant_config("vanity", "tenants")


@pytest.fixture
def knowledge_path():
    return Path("tenants/vanity/knowledge")


@pytest.fixture
def engine(tenant_config, knowledge_path):
    return TenantKnowledgeEngine(tenant_config, knowledge_path)


class TestTenantKnowledgeEngine:
    def test_loads_all_required_docs(self, engine):
        docs = engine.list_documents()
        assert "identity.md" in docs
        assert "policies.md" in docs
        assert "booking_flow.md" in docs
        assert "roles.md" in docs
        assert "escalation.md" in docs

    def test_build_system_prompt_includes_business_name(self, engine):
        prompt = engine.build_system_prompt(datetime.now(UTC))
        assert "Vanity Nail Salon" in prompt

    def test_build_system_prompt_includes_bot_name(self, engine):
        prompt = engine.build_system_prompt(datetime.now(UTC))
        assert "Sofia" in prompt

    def test_build_system_prompt_includes_booking_url(self, engine):
        prompt = engine.build_system_prompt(datetime.now(UTC))
        assert "fresha" in prompt.lower() or "fresh.com" in prompt.lower()

    def test_build_system_prompt_includes_datetime(self, engine):
        dt = datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)
        prompt = engine.build_system_prompt(dt)
        assert "2026-05-18" in prompt

    def test_build_system_prompt_includes_memory_context(self, engine):
        prompt = engine.build_system_prompt(datetime.now(UTC), memory_context="Cliente frecuente")
        assert "Cliente frecuente" in prompt

    def test_build_system_prompt_includes_catalog_hint(self, engine):
        prompt = engine.build_system_prompt(datetime.now(UTC), catalog_hint="Catálogo: Gelish $350")
        assert "Catálogo: Gelish $350" in prompt

    def test_build_system_prompt_replaces_placeholders(self, engine):
        prompt = engine.build_system_prompt(datetime.now(UTC))
        assert "{bot_display_name}" not in prompt
        assert "{business_display_name}" not in prompt
        assert "{booking_url}" not in prompt

    def test_get_document_returns_content(self, engine):
        content = engine.get_document("identity.md")
        assert content is not None
        assert "Eres" in content

    def test_get_document_returns_none_for_missing(self, engine):
        content = engine.get_document("nonexistent.md")
        assert content is None

    def test_reload_refreshes_documents(self, engine):
        docs_before = engine.list_documents()
        engine.reload()
        docs_after = engine.list_documents()
        assert docs_before == docs_after

    def test_policies_document_includes_booking_policy(self, engine):
        content = engine.get_document("policies.md")
        assert content is not None
        assert "{booking_provider}" in content

    def test_escalation_document_includes_markers(self, engine):
        content = engine.get_document("escalation.md")
        assert content is not None
        assert "{human_handover_markers}" in content

    def test_roles_document_includes_all_roles(self, engine):
        content = engine.get_document("roles.md")
        assert content is not None
        assert "frontdesk" in content.lower()
        assert "manager" in content.lower()
        assert "staff1" in content.lower()
