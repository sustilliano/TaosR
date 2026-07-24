"""Tests for the Bean-4 firewall store (tinyagentos/bean_firewall_store.py).

Covers: baseline set/get round-trip + overwrite (latest wins), unknown agent
-> None, alert append + list (newest first, per-agent isolation, limit
clamping), and the best-effort notification bridge.
"""
from __future__ import annotations

import pytest

from tinyagentos.bean_firewall import build_baseline
from tinyagentos.bean_firewall_store import BeanFirewallStore, bridge_alert_to_notifications


def _sample_baseline():
    events = [
        {"agent": "scout-1", "tool": "list_tanks", "ts": 0.0},
        {"agent": "scout-1", "tool": "fleet_status", "ts": 1.0},
        {"agent": "scout-1", "tool": "list_tanks", "ts": 2.0},
    ]
    return build_baseline(events, agent="scout-1")


@pytest.mark.asyncio
class TestBaselinePersistence:
    async def _make_store(self, db_path):
        store = BeanFirewallStore(db_path)
        await store.init()
        return store

    async def test_set_get_roundtrip(self, tmp_path):
        store = await self._make_store(tmp_path / "fw.db")
        try:
            baseline = _sample_baseline()
            await store.set_baseline("scout-1", baseline)
            got = await store.get_baseline("scout-1")
            assert got == baseline
        finally:
            await store.close()

    async def test_get_unknown_agent_returns_none(self, tmp_path):
        store = await self._make_store(tmp_path / "fw.db")
        try:
            assert await store.get_baseline("ghost") is None
        finally:
            await store.close()

    async def test_set_again_overwrites(self, tmp_path):
        store = await self._make_store(tmp_path / "fw.db")
        try:
            await store.set_baseline("scout-1", _sample_baseline())
            updated = build_baseline(
                [{"agent": "scout-1", "tool": "drive", "ts": 0.0}], agent="scout-1"
            )
            await store.set_baseline("scout-1", updated)
            got = await store.get_baseline("scout-1")
            assert got == updated
        finally:
            await store.close()

    async def test_persists_across_reopen(self, tmp_path):
        db_path = tmp_path / "fw.db"
        store = await self._make_store(db_path)
        try:
            await store.set_baseline("scout-1", _sample_baseline())
        finally:
            await store.close()

        store = await self._make_store(db_path)
        try:
            assert await store.get_baseline("scout-1") == _sample_baseline()
        finally:
            await store.close()

    async def test_uninitialised_store_raises(self, tmp_path):
        store = BeanFirewallStore(tmp_path / "fw.db")
        with pytest.raises(RuntimeError):
            await store.set_baseline("scout-1", _sample_baseline())
        with pytest.raises(RuntimeError):
            await store.get_baseline("scout-1")
        with pytest.raises(RuntimeError):
            await store.record_alert("scout-1", 0.1, ["x"])
        with pytest.raises(RuntimeError):
            await store.list_alerts("scout-1")


@pytest.mark.asyncio
class TestAlertLog:
    async def _make_store(self, db_path):
        store = BeanFirewallStore(db_path)
        await store.init()
        return store

    async def test_append_and_list_newest_first(self, tmp_path):
        store = await self._make_store(tmp_path / "fw.db")
        try:
            await store.record_alert("scout-1", 0.9, ["reason one"])
            await store.record_alert("scout-1", 0.2, ["reason two", "reason three"])
            alerts = await store.list_alerts("scout-1")
            assert len(alerts) == 2
            assert alerts[0]["score"] == 0.2
            assert alerts[0]["reasons"] == ["reason two", "reason three"]
            assert alerts[1]["score"] == 0.9
            assert all("id" in a and "ts" in a for a in alerts)
        finally:
            await store.close()

    async def test_alerts_are_per_agent(self, tmp_path):
        store = await self._make_store(tmp_path / "fw.db")
        try:
            await store.record_alert("scout-1", 0.1, ["r"])
            await store.record_alert("scout-2", 0.1, ["r"])
            assert len(await store.list_alerts("scout-1")) == 1
            assert len(await store.list_alerts("scout-2")) == 1
            assert await store.list_alerts("ghost") == []
        finally:
            await store.close()

    async def test_list_alerts_respects_limit(self, tmp_path):
        store = await self._make_store(tmp_path / "fw.db")
        try:
            for i in range(5):
                await store.record_alert("scout-1", 0.1 * i, [f"r{i}"])
            alerts = await store.list_alerts("scout-1", limit=2)
            assert len(alerts) == 2
            # Newest first.
            assert alerts[0]["reasons"] == ["r4"]
            assert alerts[1]["reasons"] == ["r3"]
        finally:
            await store.close()

    async def test_never_updated_or_deleted(self, tmp_path):
        # No mutate/delete surface exists beyond record_alert appending.
        assert not hasattr(BeanFirewallStore, "delete_alert")
        assert not hasattr(BeanFirewallStore, "update_alert")


class _FakeNotificationStore:
    def __init__(self):
        self.calls: list[dict] = []

    async def add(self, **kwargs):
        self.calls.append(kwargs)


class _ExplodingNotificationStore:
    async def add(self, **kwargs):
        raise RuntimeError("notification backend is down")


@pytest.mark.asyncio
class TestNotificationBridge:
    async def test_posts_alert_to_notification_store(self):
        notif = _FakeNotificationStore()
        await bridge_alert_to_notifications(notif, "scout-1", 0.31, ["unseen tool 'drive'"])
        assert len(notif.calls) == 1
        call = notif.calls[0]
        assert call["source"] == "bean_firewall"
        assert call["level"] == "warning"
        assert call["data"] == {
            "agent": "scout-1",
            "score": 0.31,
            "reasons": ["unseen tool 'drive'"],
        }
        assert "scout-1" in call["title"]

    async def test_never_raises_when_notification_store_fails(self):
        notif = _ExplodingNotificationStore()
        # Must not raise — best-effort bridge.
        await bridge_alert_to_notifications(notif, "scout-1", 0.1, ["x"])
