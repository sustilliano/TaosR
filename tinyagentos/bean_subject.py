from __future__ import annotations

"""Subject identity for the all-digital consent substrate
(docs/design/silicon-bean-all-digital.md).

The silicon bean covers all digital actors, not just AI agents. A consent
grant, an action receipt, or a firewall baseline is *about a subject* — and a
subject can be an agent, an installed userspace app, or whatever "all digital"
grows to next. This module is the small, shared vocabulary that names those
subjects so one ``bean_consent`` ledger can key rows for every kind.

A subject key is ``"<kind>:<ident>"`` — e.g. ``"agent:scout-1"``,
``"app:com.acme.notes"``. Kinds are deliberately open (not an enum): the
point of the all-digital framing is that new subject kinds are additive.

Backward compatibility: Bean-3 stores bare agent slugs (no ``agent:``
prefix) in ``bean_consent.agent_slug``. ``subject_key`` is therefore opt-in
— existing agent grants keep working untouched; new call sites that want to
mix agents and apps in one ledger adopt the prefixed keys.
"""

AGENT = "agent"
APP = "app"

_SEP = ":"


def subject_key(kind: str, ident: str) -> str:
    """Build a subject key ``"<kind>:<ident>"``.

    ``kind`` must be a non-empty separator-free token; ``ident`` may contain
    anything except a leading/trailing space. The kind is lowercased so
    ``Agent``/``agent`` don't fork the ledger.
    """
    kind = (kind or "").strip().lower()
    ident = (ident or "").strip()
    if not kind or _SEP in kind:
        raise ValueError(f"invalid subject kind: {kind!r}")
    if not ident:
        raise ValueError("subject ident must be non-empty")
    return f"{kind}{_SEP}{ident}"


def parse_subject(key: str) -> tuple[str, str]:
    """Split a subject key into ``(kind, ident)``.

    A key with no separator is treated as a bare agent slug — the Bean-3
    legacy shape — and returns ``("agent", key)`` so old rows read back with
    a sensible kind without a migration.
    """
    if _SEP not in key:
        return (AGENT, key)
    kind, ident = key.split(_SEP, 1)
    return (kind.lower(), ident)


def is_kind(key: str, kind: str) -> bool:
    """True iff *key* names a subject of *kind*."""
    return parse_subject(key)[0] == (kind or "").strip().lower()
