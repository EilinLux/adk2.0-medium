#!/usr/bin/env bash

set -e

# ==============================================================================
# CONFIGURATION & ENV LOADING
# ==============================================================================
ENV_FILE=".env"
VENV_PATH=".venv/bin/activate"
LOG_DIR="logs"

mkdir -p "$LOG_DIR"

echo "======================================================================"
echo "🚀 Starting Google ADK 2.0 A2A Multi-Service Stack Setup"
echo "======================================================================"

# ------------------------------------------------------------------------------
# 1. LOAD VARIABLES FROM .ENV
# ------------------------------------------------------------------------------
echo "📄 Step 1: Loading environment variables from $ENV_FILE..."

if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
    echo "  ✅ Loaded variables from $ENV_FILE."
else
    echo "  ⚠️ Warning: $ENV_FILE not found! Setting fallback variables..."
    export PROJECT_ID="adk-workshop-sosta-app-dev"
fi

# Fallback environment exports for BigQuery & GCP SDKs
PROJECT_ID="${PROJECT_ID:-adk-workshop-sosta-app-dev}"
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-$PROJECT_ID}"
export BIGQUERY_PROJECT_ID="${BIGQUERY_PROJECT_ID:-$PROJECT_ID}"

# Endpoint Ports (uses .env values if set, defaults otherwise)
MCP_PORT="${MCP_PORT:-8002}"
SUGGERITORE_PORT="${SUGGERITORE_PORT:-8001}"
CAMERIERE_PORT="${CAMERIERE_PORT:-8000}"

echo "  ↳ Target GCP Project: $GOOGLE_CLOUD_PROJECT"

# ------------------------------------------------------------------------------
# 2. VIRTUAL ENV & GCP AUTH CHECK
# ------------------------------------------------------------------------------
echo ""
echo "🔑 Step 2: Checking Virtual Environment & GCP Authentication..."

if [ -f "$VENV_PATH" ]; then
    source "$VENV_PATH"
    echo "  ✅ Virtual environment activated ($VENV_PATH)."
else
    echo "  ❌ Virtual environment not found at $VENV_PATH. Run 'uv sync' first."
    exit 1
fi

gcloud config set project "$GOOGLE_CLOUD_PROJECT" >/dev/null 2>&1 || true

# Check Application Default Credentials (ADC)
if ! gcloud auth application-default print-access-token >/dev/null 2>&1; then
    echo "  ⚠️ Application Default Credentials (ADC) not found or expired."
    echo "  🔐 Launching 'gcloud auth application-default login'..."
    gcloud auth application-default login
else
    echo "  ✅ Valid GCP ADC tokens found for project '$GOOGLE_CLOUD_PROJECT'."
fi

# Clean up any lingering processes on our microservice ports
for port in $MCP_PORT $SUGGERITORE_PORT $CAMERIERE_PORT; do
    pid=$(lsof -t -i:$port 2>/dev/null || true)
    if [ -n "$pid" ]; then
        echo "  🧹 Cleaning up stale process $pid on port $port..."
        kill -9 "$pid" 2>/dev/null || true
    fi
done

# ------------------------------------------------------------------------------
# 3. TEARDOWN FUNCTION (GRACEFUL CLEANUP ON EXIT)
# ------------------------------------------------------------------------------
cleanup() {
    echo ""
    echo "======================================================================"
    echo "🛑 Shutting down all A2A microservices and background jobs..."
    echo "======================================================================"
    
    pkill -P $$ 2>/dev/null || true
    
    for port in $MCP_PORT $SUGGERITORE_PORT $CAMERIERE_PORT; do
        pid=$(lsof -t -i:$port 2>/dev/null || true)
        if [ -n "$pid" ]; then
            kill -9 "$pid" 2>/dev/null || true
        fi
    done
    
    echo "✅ Shutdown complete."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# ------------------------------------------------------------------------------
# 4. LAUNCH SERVICE 1: FASTMCP SERVER (Port 8002)
# ------------------------------------------------------------------------------
echo ""
echo "📡 Step 3: Launching FastMCP BigQuery GIS Server on Port $MCP_PORT..."

# Dynamically resolve file location across possible refactored paths
MCP_SCRIPT_PATH=""
if [ -f "adk_agent_app_suggeritore/tools/suggeritore_agent_bq_mcp_soste_tool.py" ]; then
    MCP_SCRIPT_PATH="adk_agent_app_suggeritore/tools/suggeritore_agent_bq_mcp_soste_tool.py"
elif [ -f "adk_agent_app/tools/suggeritore_agent_bq_mcp_soste_tool.py" ]; then
    MCP_SCRIPT_PATH="adk_agent_app/tools/suggeritore_agent_bq_mcp_soste_tool.py"
else
    # Auto-discover via find command if paths moved
    MCP_SCRIPT_PATH=$(find . -maxdepth 4 -name "*mcp_soste_tool.py" | head -n 1)
fi

# Guard check: Ensure a valid script path was discovered
if [ -z "$MCP_SCRIPT_PATH" ] || [ ! -f "$MCP_SCRIPT_PATH" ]; then
    echo "❌ ERROR: Cannot locate 'suggeritore_agent_bq_mcp_soste_tool.py' in project!"
    echo "   Please check where your FastMCP Python script is saved."
    exit 1
fi

echo "  ↳ Found script at: $MCP_SCRIPT_PATH"

python "$MCP_SCRIPT_PATH" > "$LOG_DIR/mcp_server.log" 2>&1 &
MCP_PID=$!
echo "  ↳ FastMCP PID: $MCP_PID (Logs: $LOG_DIR/mcp_server.log)"

echo "  ⌛ Waiting for FastMCP Server to open port $MCP_PORT..."

# Socket check on TCP port 8002
while ! python3 -c "import socket; s = socket.socket(); s.settimeout(1); exit(0 if s.connect_ex(('127.0.0.1', $MCP_PORT)) == 0 else 1)" 2>/dev/null; do
    if ! kill -0 $MCP_PID 2>/dev/null; then
        echo ""
        echo "❌ ERROR: FastMCP server process exited or crashed!"
        echo "📋 Check log file: $LOG_DIR/mcp_server.log"
        echo "------------------ LAST LOG LINES ------------------"
        tail -n 25 "$LOG_DIR/mcp_server.log"
        echo "----------------------------------------------------"
        exit 1
    fi
    sleep 1
done
echo "  ✅ FastMCP BigQuery Server is live on port $MCP_PORT!"

# ------------------------------------------------------------------------------
# 5. LAUNCH SERVICE 2: SUGGERITORE A2A AGENT APP (Port 8001)
# ------------------------------------------------------------------------------
echo ""
echo "🤖 Step 4: Launching Suggeritore A2A Microservice on Port $SUGGERITORE_PORT..."
# Export explicitly for child processes
export GOOGLE_GENAI_USE_VERTEXAI="${GOOGLE_GENAI_USE_VERTEXAI:-true}"

uvicorn adk_agent_app_suggeritore.agent:a2a_app --host 127.0.0.1 --port $SUGGERITORE_PORT \
    > "$LOG_DIR/suggeritore_app.log" 2>&1 &

SUGGERITORE_PID=$!
echo "  ↳ Suggeritore A2A PID: $SUGGERITORE_PID (Logs: $LOG_DIR/suggeritore_app.log)"

echo "  ⌛ Waiting for Suggeritore Agent Card on http://localhost:$SUGGERITORE_PORT..."

while true; do
    if ! kill -0 $SUGGERITORE_PID 2>/dev/null; then
        echo ""
        echo "❌ ERROR: Suggeritore process crashed on startup!"
        echo "📋 Check log file: $LOG_DIR/suggeritore_app.log"
        tail -n 25 "$LOG_DIR/suggeritore_app.log"
        exit 1
    fi

    # Check for HTTP 200 on the official agent-card route
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 1 "http://localhost:$SUGGERITORE_PORT/.well-known/agent-card.json" || true)

    if [ "$HTTP_STATUS" -eq 200 ]; then
        FOUND_CARD="http://localhost:$SUGGERITORE_PORT/.well-known/agent-card.json"
        break
    fi

    sleep 1
done

echo "  ✅ Suggeritore Agent Card is online at: $FOUND_CARD"

# ------------------------------------------------------------------------------
# 6. LAUNCH SERVICE 3: CAMERIERE PRIMARY AGENT APP + WEB UI (Port 8000)
# ------------------------------------------------------------------------------
echo ""
echo "🤵 Step 5: Launching Cameriere Agent with ADK Web UI on Port $CAMERIERE_PORT..."

# Launching 'adk web' hosts both the API and the interactive browser UI
adk web adk_agent_app --port $CAMERIERE_PORT \
    > "$LOG_DIR/cameriere_app.log" 2>&1 &

CAMERIERE_PID=$!
echo "  ↳ Cameriere Web UI PID: $CAMERIERE_PID (Logs: $LOG_DIR/cameriere_app.log)"

echo "  ⌛ Waiting for Cameriere Agent & Web UI on http://localhost:$CAMERIERE_PORT..."
while ! python3 -c "import socket; s = socket.socket(); s.settimeout(1); exit(0 if s.connect_ex(('127.0.0.1', $CAMERIERE_PORT)) == 0 else 1)" 2>/dev/null; do
    if ! kill -0 $CAMERIERE_PID 2>/dev/null; then
        echo ""
        echo "❌ ERROR: Cameriere Agent crashed on startup!"
        tail -n 25 "$LOG_DIR/cameriere_app.log"
        exit 1
    fi
    sleep 1
done
echo "  ✅ Cameriere Client Agent & Web UI are online!"

# ------------------------------------------------------------------------------
# 7. RUN HEALTH CHECK TEST QUERY
# ------------------------------------------------------------------------------
echo ""
echo "======================================================================"
echo "🧪 Running End-to-End Test Request via Cameriere Agent..."
echo "======================================================================"

TEST_PAYLOAD='{
  "app_name": "adk_agent_app",
  "user_content": "Hello."
}'

echo "  📤 Sending POST request to http://localhost:$CAMERIERE_PORT/run_sse..."
echo ""

curl -s -X POST "http://localhost:$CAMERIERE_PORT/run_sse" \
  -H "Content-Type: application/json" \
  -d "$TEST_PAYLOAD" || true


echo ""
echo ""
echo "======================================================================"
echo "🎉 All services are running successfully!"
echo "======================================================================"
echo "🔗 CLICKABLE ENDPOINTS TO VERIFY & TEST:"
echo ""
echo "  1. 🤖 Suggeritore A2A Agent Card (Port $SUGGERITORE_PORT):"
echo "     👉 http://localhost:$SUGGERITORE_PORT/.well-known/agent-card.json"
echo ""
echo "  2. 📡 FastMCP SSE Tool Stream (Port $MCP_PORT):"
echo "     👉 http://127.0.0.1:$MCP_PORT/sse"
echo ""
echo "  3. 🤵 Cameriere Client SSE Endpoint (Port $CAMERIERE_PORT):"
echo "     👉 http://localhost:$CAMERIERE_PORT/run_sse"
echo ""
echo "  4. 🛠️ ADK Developer Web UI (Port $CAMERIERE_PORT):"
echo "     👉 http://localhost:$CAMERIERE_PORT/dev-ui/"
echo ""
echo "======================================================================"
echo "📋 QUICK COMMANDS TO TEST IN A NEW TERMINAL:"
echo ""
echo "  • Verify Agent Card metadata:"
echo "    curl -s http://localhost:$SUGGERITORE_PORT/.well-known/agent-card.json | jq ."
echo ""
echo "  • Tail live log output across all services:"
echo "    tail -f $LOG_DIR/mcp_server.log $LOG_DIR/suggeritore_app.log $LOG_DIR/cameriere_app.log"
echo "======================================================================"
echo "💡 Press [CTRL+C] at any time to shut down all microservices."


wait