#!/usr/bin/env bash
set -euo pipefail

ROLE="${SERVICE_ROLE:-runner}"
LISTEN_PORT="${PORT:-8080}"

echo "============================================================"
echo " Starting SostaApp Container | SERVICE_ROLE=${ROLE} | PORT=${LISTEN_PORT}"
echo "============================================================"

case "${ROLE}" in
  mcp)
    export PORT="${LISTEN_PORT}"
    export MCP_HOST="0.0.0.0"
    exec python adk_agent_app_suggeritore/tools/suggeritore_agent_bq_mcp_soste_tool.py
    ;;
  a2a)
    exec uvicorn adk_agent_app_suggeritore.agent:a2a_app \
      --host 0.0.0.0 \
      --port "${LISTEN_PORT}" \
      --proxy-headers \
      --forwarded-allow-ips="*"
    ;;
  runner)
    export SKIP_PREFLIGHT_CHECKS="${SKIP_PREFLIGHT_CHECKS:-true}"
    exec uvicorn adk_agent_app.server:app \
      --host 0.0.0.0 \
      --port "${LISTEN_PORT}" \
      --proxy-headers \
      --forwarded-allow-ips="*"
    ;;
  web)
    export SKIP_PREFLIGHT_CHECKS="${SKIP_PREFLIGHT_CHECKS:-true}"
    exec adk web --host 0.0.0.0 --port "${LISTEN_PORT}"
    ;;
  *)
    echo "ERROR: Unknown SERVICE_ROLE '${ROLE}'. Expected one of: mcp, a2a, runner, web." >&2
    exit 1
    ;;
esac
