"""Tests for the all-digital consent spine
(docs/design/silicon-bean-all-digital.md): subject keys + the
subject-agnostic gated_consent_check that both agent and app gates share.
"""
from __future__ import annotations

import pytest

from tinyagentos import bean_subject
from tinyagentos.bean_consent import (
    FLAGGED_SCOPES,
    consent_check,
    gated_consent_check,
    is_flagged_scope,
)


class TestSubjectKeys:
    def test_build_and_parse_roundtrip(self):
        k = bean_subject.subject_key("app", "com.acme.notes")
        assert k == "app:com.acme.notes"
        assert bean_subject.parse_subject(k) == ("app", "com.acme.notes")

    def test_kind_is_lowercased(self):
        assert bean_subject.subject_key("Agent", "scout-1") == "agent:scout-1"

    def test_bare_slug_parses_as_legacy_agent(self):
        # Bean-3 stored bare agent slugs; they read back as agent subjects
        # with no migration.
        assert bean_subject.parse_subject("scout-1") == ("agent", "scout-1")
        assert bean_subject.is_kind("scout-1", "agent")

    def test_ident_may_contain_colons(self):
        # split on the FIRST separator only — idents can hold colons.
        k = bean_subject.subject_key("app", "com.acme:v2")
        assert bean_subject.parse_subject(k) == ("app", "com.acme:v2")

    def test_invalid_inputs_rejected(self):
        with pytest.raises(ValueError):
            bean_subject.subject_key("", "x")
        with pytest.raises(ValueError):
            bean_subject.subject_key("a:b", "x")  # kind can't contain sep
        with pytest.raises(ValueError):
            bean_subject.subject_key("app", "")


class TestSubjectValidation:
    def test_bare_agent_slug_valid(self):
        assert bean_subject.is_valid_subject("scout-1")
        assert bean_subject.is_valid_subject("agent_42.v2")

    def test_app_subject_key_valid(self):
        assert bean_subject.is_valid_subject("app:open-cowork")
        assert bean_subject.is_valid_subject("app:com.acme.notes")

    def test_path_traversal_and_separators_rejected(self):
        assert not bean_subject.is_valid_subject("../etc")
        assert not bean_subject.is_valid_subject("app:../x")
        assert not bean_subject.is_valid_subject("a/b")
        assert not bean_subject.is_valid_subject("app:a/b")
        assert not bean_subject.is_valid_subject("")

    def test_bad_kind_or_ident_rejected(self):
        assert not bean_subject.is_valid_subject("app:")     # empty ident
        assert not bean_subject.is_valid_subject(":x")       # empty kind
        assert not bean_subject.is_valid_subject("app: x")   # space


class TestGatedConsentCheck:
    def test_non_gated_scope_always_allowed(self):
        allowed, reason = gated_consent_check(
            "anything", is_gated=lambda s: False, is_allowed_fn=lambda s: False
        )
        assert allowed is True and reason is None

    def test_gated_and_granted(self):
        allowed, reason = gated_consent_check(
            "app.net", is_gated=lambda s: True, is_allowed_fn=lambda s: True
        )
        assert allowed is True and reason is None

    def test_gated_and_not_granted_denies_with_reason(self):
        allowed, reason = gated_consent_check(
            "app.net", is_gated=lambda s: True, is_allowed_fn=lambda s: False,
            denial_reason="app capability requires consent",
        )
        assert allowed is False
        assert reason == "app capability requires consent"

    def test_default_denial_reason(self):
        allowed, reason = gated_consent_check(
            "x", is_gated=lambda s: True, is_allowed_fn=lambda s: False
        )
        assert allowed is False and reason  # falls back to the Bean-3 reason

    def test_app_broker_style_gate(self):
        # Emulate the userspace broker's GATED_CAPS gate riding the shared core.
        GATED_CAPS = {"app.net", "app.llm", "app.agent", "app.memory"}

        def is_gated(cap: str) -> bool:
            ns = ".".join(cap.split(".")[:2])
            return ns in GATED_CAPS

        granted = {"app.net"}
        # granted namespace -> allowed
        assert gated_consent_check("app.net.fetch", is_gated,
                                   lambda c: ".".join(c.split(".")[:2]) in granted)[0] is True
        # ungranted gated namespace -> denied
        assert gated_consent_check("app.llm.complete", is_gated,
                                   lambda c: ".".join(c.split(".")[:2]) in granted)[0] is False
        # free namespace -> allowed regardless
        assert gated_consent_check("app.kv.get", is_gated, lambda c: False)[0] is True


class TestBean3Unchanged:
    """consent_check must behave exactly as before the refactor."""

    def test_non_flagged_tool_allowed(self):
        assert consent_check("list_tanks", lambda s: False) == (True, None)

    def test_flagged_tool_needs_grant(self):
        assert consent_check("drive", lambda s: False)[0] is False
        assert consent_check("drive", lambda s: True) == (True, None)

    def test_every_flagged_scope_gated(self):
        for scope in FLAGGED_SCOPES:
            assert is_flagged_scope(scope)
            assert consent_check(scope, lambda s: False)[0] is False
