#!/usr/bin/env bash
# Bean-0 static checks for the Hermes installer: the framework installer is
# downloaded-then-hashed (no curl|bash), the constitution file is written and
# hash-pinned, and the provenance record carries every required key.
# Dependency-free: bash + grep/sed only; never executes the installer.
set -euo pipefail
SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/tinyagentos/scripts/install_hermes.sh"

echo "test: bash -n syntax (install_hermes.sh)"
bash -n "$SCRIPT"

echo "test: no curl|bash remains (installer must be downloaded, then executed)"
if grep -E 'curl[^|]*\|\s*(ba)?sh' "$SCRIPT" | grep -v 'astral.sh/uv' | grep -q .; then
  echo "FAIL: install_hermes.sh still pipes a remote installer straight into bash"
  grep -nE 'curl[^|]*\|\s*(ba)?sh' "$SCRIPT" | grep -v 'astral.sh/uv'
  exit 1
fi
echo "PASS: hermes installer is no longer piped into bash"

echo "test: installer is downloaded to a file, hashed, then executed"
grep -q -- '-o /tmp/hermes-install.sh' "$SCRIPT" \
  || { echo "FAIL: installer is not downloaded to /tmp/hermes-install.sh"; exit 1; }
grep -q 'INSTALLER_SHA256=\$(sha256sum /tmp/hermes-install.sh' "$SCRIPT" \
  || { echo "FAIL: INSTALLER_SHA256 is not computed over the downloaded installer"; exit 1; }
grep -q 'bash /tmp/hermes-install.sh --skip-setup' "$SCRIPT" \
  || { echo "FAIL: downloaded installer is not executed with --skip-setup"; exit 1; }
# hash must be computed before execution
hash_line=$(grep -n 'INSTALLER_SHA256=\$(sha256sum' "$SCRIPT" | cut -d: -f1 | head -1)
exec_line=$(grep -n 'bash /tmp/hermes-install.sh' "$SCRIPT" | cut -d: -f1 | head -1)
if [ "$hash_line" -ge "$exec_line" ]; then
  echo "FAIL: installer is executed (line $exec_line) before it is hashed (line $hash_line)"
  exit 1
fi
echo "PASS: download -> sha256 -> execute, in that order"

echo "test: framework ref is pinned and env-overridable (default main)"
grep -q 'HERMES_RELEASE="\${TAOS_HERMES_RELEASE:-main}"' "$SCRIPT" \
  || { echo "FAIL: HERMES_RELEASE pin missing or default changed"; exit 1; }
grep -q 'hermes-agent/\${HERMES_RELEASE}/scripts/install.sh' "$SCRIPT" \
  || { echo "FAIL: installer URL does not use \${HERMES_RELEASE}"; exit 1; }
echo "PASS: framework ref pinned via TAOS_HERMES_RELEASE (fallback main)"

echo "test: preinstalled fast path records installer_sha256=preinstalled"
grep -q 'INSTALLER_SHA256="preinstalled"' "$SCRIPT" \
  || { echo "FAIL: already-installed path does not set INSTALLER_SHA256=preinstalled"; exit 1; }
echo "PASS: preinstalled fast path keeps provenance populated"

echo "test: constitution heredoc exists and is hash-pinned"
grep -q 'cat > /opt/taos/constitution.txt <<' "$SCRIPT" \
  || { echo "FAIL: constitution.txt heredoc missing"; exit 1; }
grep -q 'CONSTITUTION_SHA256=\$(sha256sum /opt/taos/constitution.txt' "$SCRIPT" \
  || { echo "FAIL: CONSTITUTION_SHA256 not computed over constitution.txt"; exit 1; }
echo "PASS: constitution written and hashed"

echo "test: bridge reads constitution.txt with embedded fallback"
grep -q '_CONSTITUTION_PATH = "/opt/taos/constitution.txt"' "$SCRIPT" \
  || { echo "FAIL: bridge does not read /opt/taos/constitution.txt"; exit 1; }
grep -q '_FALLBACK_SYSTEM_PROMPT' "$SCRIPT" \
  || { echo "FAIL: bridge lost its embedded fallback prompt"; exit 1; }
echo "PASS: bridge prefers the constitution file, falls back to embedded text"

echo "test: provenance.json heredoc carries all required keys"
prov="$(sed -n '/cat > \/opt\/taos\/provenance.json <<PROVEOF/,/^PROVEOF$/p' "$SCRIPT")"
if [ -z "$prov" ]; then
  echo "FAIL: provenance.json heredoc not found"
  exit 1
fi
for key in substrate framework framework_ref installer_sha256 constitution_sha256 \
           model_id corpus_refs recorded_at; do
  if ! grep -q "\"$key\"" <<<"$prov"; then
    echo "FAIL: provenance.json is missing required key: $key"
    exit 1
  fi
done
grep -q '"substrate": "silicon"' <<<"$prov" \
  || { echo "FAIL: substrate must be the literal \"silicon\""; exit 1; }
grep -q 'teknium/OpenHermes-2.5' <<<"$prov" \
  || { echo "FAIL: corpus_refs must reference the OpenHermes-2.5 dataset"; exit 1; }
echo "PASS: provenance record has all Bean-0 keys"

echo "test: provenance POST to controller is best-effort (|| fallback)"
grep -q '/api/agents/\$AGENT_NAME/provenance' "$SCRIPT" \
  || { echo "FAIL: no provenance POST to the controller"; exit 1; }
grep -A5 '/api/agents/\$AGENT_NAME/provenance' "$SCRIPT" | grep -q '|| log' \
  || { echo "FAIL: provenance POST is not best-effort (missing || log fallback)"; exit 1; }
echo "PASS: provenance POST cannot fail the install"

echo "all tests passed"
