"""Track 1 (memory_systems on deploy) — deployer._memory_env unit tests.

Covers the env vars deploy_agent injects for an agent's memory-plane
selection: TAOS_MEMORY_SYSTEMS always, TAOS_TMRFS_AGENT only when "tmrfs" is
selected. Also covers the DeployRequest.memory_systems field default.

Run standalone (no full backend venv needed):

    pytest tests/memory_systems/ --confcutdir=tests/memory_systems
"""
from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from tinyagentos.deployer import DeployRequest, _memory_env


class TestMemoryEnv:

    def test_taosmd_only_sets_no_tmrfs_vars(self):
        env = _memory_env(["taosmd"], "scout-1")
        assert env == {"TAOS_MEMORY_SYSTEMS": "taosmd"}
        assert "TAOS_TMRFS_AGENT" not in env

    def test_taosmd_tmrfs_sets_agent_and_comma_list(self):
        env = _memory_env(["taosmd", "tmrfs"], "scout-1")
        assert env["TAOS_MEMORY_SYSTEMS"] == "taosmd,tmrfs"
        assert env["TAOS_TMRFS_AGENT"] == "scout-1"

    def test_pk_trust_alone_sets_memory_systems_no_tmrfs_agent(self):
        env = _memory_env(["pk-trust"], "scout-1")
        assert env["TAOS_MEMORY_SYSTEMS"] == "pk-trust"
        assert "TAOS_TMRFS_AGENT" not in env

    def test_all_three_selected(self):
        env = _memory_env(["taosmd", "tmrfs", "pk-trust"], "scout-9")
        assert env["TAOS_MEMORY_SYSTEMS"] == "taosmd,tmrfs,pk-trust"
        assert env["TAOS_TMRFS_AGENT"] == "scout-9"

    def test_none_defaults_to_taosmd(self):
        env = _memory_env(None, "scout-1")
        assert env == {"TAOS_MEMORY_SYSTEMS": "taosmd"}

    def test_empty_list_defaults_to_taosmd(self):
        env = _memory_env([], "scout-1")
        assert env == {"TAOS_MEMORY_SYSTEMS": "taosmd"}

    def test_agent_name_namespaces_tmrfs_agent_var(self):
        """Different agent names must produce distinct TAOS_TMRFS_AGENT values
        (the whole point of the auto-namespacing)."""
        env_a = _memory_env(["tmrfs"], "agent-a")
        env_b = _memory_env(["tmrfs"], "agent-b")
        assert env_a["TAOS_TMRFS_AGENT"] == "agent-a"
        assert env_b["TAOS_TMRFS_AGENT"] == "agent-b"
        assert env_a["TAOS_TMRFS_AGENT"] != env_b["TAOS_TMRFS_AGENT"]


class TestDeployRequestMemorySystemsField:

    def test_default_is_taosmd_only(self):
        req = DeployRequest(
            name="scout-1", framework="none", model=None, data_dir=Path("/tmp/x"),
        )
        assert req.memory_systems == ["taosmd"]

    def test_field_is_settable(self):
        req = DeployRequest(
            name="scout-1", framework="none", model=None, data_dir=Path("/tmp/x"),
            memory_systems=["taosmd", "tmrfs"],
        )
        assert req.memory_systems == ["taosmd", "tmrfs"]

    def test_default_factory_is_independent_per_instance(self):
        """Mutating one instance's list must not leak into another's default
        (guards against a shared-mutable-default bug)."""
        req1 = DeployRequest(name="a", framework="none", model=None, data_dir=Path("/tmp/x"))
        req2 = DeployRequest(name="b", framework="none", model=None, data_dir=Path("/tmp/x"))
        req1.memory_systems.append("tmrfs")
        assert req2.memory_systems == ["taosmd"]

    def test_mcp_store_defaults_to_none(self):
        req = DeployRequest(name="scout-1", framework="none", model=None, data_dir=Path("/tmp/x"))
        assert req.mcp_store is None

    def test_existing_positional_and_keyword_construction_still_works(self):
        """Regression guard: adding memory_systems/mcp_store must not disturb
        existing DeployRequest callers that pass only the original fields."""
        req = DeployRequest(
            name="scout-1",
            framework="openclaw",
            model="some-model",
            data_dir=Path("/tmp/x"),
            fallback_models=["fallback-model"],
            color="#123456",
            emoji="🤖",
            memory_limit="512m",
            cpu_limit=2,
            extra_config={"foo": "bar"},
            can_read_user_memory=True,
            taos_host="127.0.0.1",
            taos_port=6969,
            remote=None,
            root_size_gib=10,
            secrets_store=None,
        )
        field_names = {f.name for f in fields(req)}
        assert "memory_systems" in field_names
        assert "mcp_store" in field_names
        assert req.memory_systems == ["taosmd"]
        assert req.mcp_store is None
