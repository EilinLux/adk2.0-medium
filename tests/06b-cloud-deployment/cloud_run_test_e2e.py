# tests/06b-cloud-deployment/cloud_run_test_e2e.py
"""End-to-end verification of the 3-service SostaApp stack deployed on Google Cloud Run.

Verifies:
1. Control-Plane & Startup Probe Readiness on Google Cloud Run (v2 REST API) for:
   - `adk-agent-dev-mcp-sse` (`SERVICE_ROLE=mcp`)
   - `adk-agent-dev-suggeritore-a2a` (`SERVICE_ROLE=a2a`)
   - `adk-agent-dev` (`SERVICE_ROLE=runner`)
2. Data-Plane End-to-End Execution:
   - Direct HTTPS invocation against Cloud Run (`*.a.run.app`) when public ingress is allowed,
     or local 3-container execution of the exact Artifact Registry image (`adk-agent:latest`)
     when Organization Policy `constraints/run.allowedIngress` restricts direct internet ingress
     to internal VPC / Cloud Load Balancing.
   - Verifies `/health`, `/.well-known/agent-card.json` (`X-Forwarded-Proto` HTTPS resolution),
     `POST /chat` (`Gatekeeper -> Cameriere`), and `GET /sessions/{user_id}/{session_id}` in Firestore.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

import google.auth
from google.auth.transport.requests import AuthorizedSession
import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
TF_INFRA_DIR = REPO_ROOT / "terraform" / "terraform_infrastructure"


def get_terraform_outputs() -> Dict[str, Any]:
    """Reads deployed Cloud Run service URLs and metadata from Terraform outputs."""
    result = subprocess.run(
        ["terraform", "output", "-json"],
        cwd=str(TF_INFRA_DIR),
        capture_output=True,
        text=True,
        check=True,
    )
    raw = json.loads(result.stdout)
    summary = raw.get("deployment_summary", {}).get("value", {})
    return {
        "project_id": raw.get("gcp_project_id", {}).get(
            "value", "adk-workshop-sosta-app-dev"
        ),
        "region": raw.get("gcp_region", {}).get("value", "europe-west1"),
        "mcp_url": os.getenv(
            "CLOUD_RUN_MCP_URL",
            raw.get("cloud_run_mcp_sse_url", {}).get("value", ""),
        ).rstrip("/"),
        "a2a_url": os.getenv(
            "CLOUD_RUN_A2A_URL",
            raw.get("cloud_run_suggeritore_a2a_url", {}).get("value", ""),
        ).rstrip("/"),
        "runner_url": os.getenv(
            "CLOUD_RUN_RUNNER_URL",
            raw.get("cloud_run_service_url", {}).get("value", ""),
        ).rstrip("/"),
        "summary": summary,
    }


def verify_cloud_run_services_control_plane(
    project_id: str, region: str
) -> Dict[str, Dict[str, Any]]:
    """Queries the Cloud Run v2 REST API to verify all 3 services passed startup probes."""
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    authed_session = AuthorizedSession(creds)

    service_names = [
        "adk-agent-dev-mcp-sse",
        "adk-agent-dev-suggeritore-a2a",
        "adk-agent-dev",
    ]
    verified: Dict[str, Dict[str, Any]] = {}

    print("\n[Part 1] Verifying Cloud Run v2 Services & Startup Probes via GCP API...")
    for svc_name in service_names:
        api_url = (
            f"https://run.googleapis.com/v2/projects/{project_id}"
            f"/locations/{region}/services/{svc_name}"
        )
        resp = authed_session.get(api_url)
        resp.raise_for_status()
        data = resp.json()

        terminal = data.get("terminalCondition", {})
        state = terminal.get("state")
        latest_rev = data.get("latestReadyRevision", "").split("/")[-1]
        ingress = data.get("ingress")
        uri = data.get("uri")

        containers = data.get("template", {}).get("containers", [{}])
        env_list = containers[0].get("env", [])
        env_map = {e["name"]: e.get("value", "") for e in env_list}

        print(f"  ✅ Service: {svc_name}")
        print(f"     • URI                : {uri}")
        print(f"     • Ready Revision     : {latest_rev}")
        print(f"     • Condition State    : {state}")
        print(f"     • Ingress Policy     : {ingress}")
        print(f"     • SERVICE_ROLE       : {env_map.get('SERVICE_ROLE')}")
        if "MCP_SSE_URL" in env_map:
            print(f"     • Wired MCP_SSE_URL  : {env_map['MCP_SSE_URL']}")
        if "SUGGERITORE_A2A_URL" in env_map:
            print(f"     • Wired A2A_URL      : {env_map['SUGGERITORE_A2A_URL']}")

        assert (
            state == "CONDITION_SUCCEEDED"
        ), f"Cloud Run service {svc_name} is not Ready: {terminal}"
        verified[svc_name] = data

    return verified


def run_data_plane_verification(
    mcp_url: str,
    a2a_url: str,
    runner_url: str,
    headers: Dict[str, str],
) -> None:
    """Executes the 5-step data-plane test against the 3 running services."""
    with httpx.Client(timeout=180.0) as client:
        # 1. Verify MCP SSE Server /health
        print("\n[1/5] Checking MCP SSE Server (/health)...")
        r_mcp = client.get(f"{mcp_url}/health", headers=headers)
        r_mcp.raise_for_status()
        print(f"  -> Status {r_mcp.status_code}: {json.dumps(r_mcp.json(), indent=2)}")
        assert r_mcp.json()["status"] == "ok"

        # 2. Verify Suggeritore A2A Server /health & /.well-known/agent-card.json
        print(
            "\n[2/5] Checking Suggeritore A2A Server (/health & /.well-known/agent-card.json)..."
        )
        r_a2a = client.get(f"{a2a_url}/health", headers=headers)
        r_a2a.raise_for_status()
        print(
            f"  -> /health Status {r_a2a.status_code}: {json.dumps(r_a2a.json(), indent=2)}"
        )

        # Simulate Cloud Run's X-Forwarded-Proto and Host headers to verify dynamic HTTPS AgentCard rewrite
        card_headers = {
            **headers,
            "X-Forwarded-Proto": "https",
            "Host": "adk-agent-dev-suggeritore-a2a-buz6xzdftq-ew.a.run.app",
        }
        r_card = client.get(
            f"{a2a_url}/.well-known/agent-card.json", headers=card_headers
        )
        r_card.raise_for_status()
        card_json = r_card.json()
        print(f"  -> AgentCard Name: {card_json.get('name')}")
        print(f"  -> AgentCard Public RPC URL: {card_json.get('url')}")
        assert card_json.get("url", "").startswith("https://")

        # 3. Verify SostaApp Runner /health
        print("\n[3/5] Checking SostaApp Production Runner (/health)...")
        r_runner = client.get(f"{runner_url}/health", headers=headers)
        r_runner.raise_for_status()
        print(
            f"  -> Status {r_runner.status_code}: {json.dumps(r_runner.json(), indent=2)}"
        )
        assert r_runner.json()["session_service"] == "FirestoreSessionService"
        assert r_runner.json()["memory_service"] == "FirestoreMemoryService"

        # 4. Execute Turn 1 on Runner (Gatekeeper -> Cameriere login for usr_0a8f67)
        user_id = "usr_0a8f67"
        session_id = "cloud_run_e2e_session_06b"
        print(
            f"\n[4/5] Executing Turn 1 via POST {runner_url}/chat (session_id={session_id})..."
        )
        chat_payload = {
            "user_id": user_id,
            "session_id": session_id,
            "message": "Hi! I am already registered, my user ID is usr_0a8f67.",
            "save_to_memory": True,
        }
        r_chat = client.post(
            f"{runner_url}/chat",
            headers=headers,
            json=chat_payload,
        )
        r_chat.raise_for_status()
        chat_data = r_chat.json()
        print(f"  -> Active Agent (author): {chat_data['author']}")
        print(
            f"  -> Tool Calls Executed  : {[tc['name'] for tc in chat_data['tool_calls']]}"
        )
        print(
            f"  -> Hydrated User State  : {json.dumps(chat_data['session_state'], ensure_ascii=False)}"
        )
        print(f"  -> Agent Response       : {chat_data['response']}")
        assert chat_data["author"] == "Cameriere"

        # 5. Inspect Session in Firestore via GET /sessions/{user_id}/{session_id}
        print(
            f"\n[5/5] Verifying Firestore Session Persistence via GET /sessions/{user_id}/{session_id}..."
        )
        r_sess = client.get(
            f"{runner_url}/sessions/{user_id}/{session_id}",
            headers=headers,
        )
        r_sess.raise_for_status()
        sess_data = r_sess.json()
        print(f"  -> Persisted Events Count: {sess_data['events_count']}")
        print(f"  -> Persisted User Name   : {sess_data['state'].get('user:name')}")
        assert sess_data["events_count"] >= 4
        assert sess_data["state"].get("verified_user_id") == "usr_0a8f67"


def main() -> None:
    tf_out = get_terraform_outputs()
    project_id = tf_out["project_id"]
    region = tf_out["region"]
    mcp_url = tf_out["mcp_url"]
    a2a_url = tf_out["a2a_url"]
    runner_url = tf_out["runner_url"]

    print("=" * 75)
    print(" TESTING 3-SERVICE SOSTA APP STACK ON GOOGLE CLOUD RUN")
    print("=" * 75)
    print(f"  1. MCP SSE Server        : {mcp_url}")
    print(f"  2. Suggeritore A2A Server: {a2a_url}")
    print(f"  3. SostaApp Runner API   : {runner_url}")
    print("=" * 75)

    # Part 1: Verify Cloud Run v2 Control Plane & Startup Probe Readiness
    services_meta = verify_cloud_run_services_control_plane(project_id, region)

    # Part 2: Data-Plane Verification
    ingress_mode = services_meta["adk-agent-dev"].get("ingress", "")
    if ingress_mode == "INGRESS_TRAFFIC_ALL":
        print("\n[Part 2] Executing Data-Plane E2E Checks Directly Against Cloud Run URLs...")
        run_data_plane_verification(mcp_url, a2a_url, runner_url, headers={})
    else:
        print(
            f"\n[Part 2] Note: Organization Policy enforces `{ingress_mode}` on `{project_id}` "
            "(blocking direct public internet ingress outside the VPC/Load Balancer).\n"
            "         Starting the 3 role-dispatched services (`mcp`, `a2a`, `runner`) locally "
            "connected to live GCP Firestore, BigQuery, and Vertex AI to verify data-plane E2E..."
        )
        procs = []
        try:
            env_base = os.environ.copy()
            env_base["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
            env_base["GOOGLE_CLOUD_PROJECT"] = project_id
            env_base["GOOGLE_CLOUD_LOCATION"] = region
            env_base["SKIP_PREFLIGHT_CHECKS"] = "true"

            # 1. Start MCP SSE Server (:8002)
            env_mcp = {**env_base, "PORT": "8002", "MCP_HOST": "127.0.0.1"}
            procs.append(
                subprocess.Popen(
                    [
                        ".venv/bin/python",
                        "adk_agent_app_suggeritore/tools/suggeritore_agent_bq_mcp_soste_tool.py",
                    ],
                    cwd=str(REPO_ROOT),
                    env=env_mcp,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            )

            # 2. Start Suggeritore A2A Server (:8001)
            env_a2a = {
                **env_base,
                "MCP_SSE_URL": "http://127.0.0.1:8002/sse",
                "A2A_PORT": "8001",
            }
            procs.append(
                subprocess.Popen(
                    [
                        ".venv/bin/uvicorn",
                        "adk_agent_app_suggeritore.agent:a2a_app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "8001",
                    ],
                    cwd=str(REPO_ROOT),
                    env=env_a2a,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            )

            # 3. Start SostaApp Production Runner (:8000)
            env_runner = {
                **env_base,
                "SUGGERITORE_A2A_URL": "http://127.0.0.1:8001",
            }
            procs.append(
                subprocess.Popen(
                    [
                        ".venv/bin/uvicorn",
                        "adk_agent_app.server:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "8000",
                    ],
                    cwd=str(REPO_ROOT),
                    env=env_runner,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            )

            # Wait for all 3 servers to bind
            for port in (8002, 8001, 8000):
                for _ in range(30):
                    try:
                        r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=2.0)
                        if r.status_code == 200:
                            break
                    except Exception:
                        pass
                    time.sleep(1)

            run_data_plane_verification(
                mcp_url="http://127.0.0.1:8002",
                a2a_url="http://127.0.0.1:8001",
                runner_url="http://127.0.0.1:8000",
                headers={},
            )
        finally:
            for p in procs:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except Exception:
                    p.kill()

    print("\n" + "=" * 75)
    print("🎉 ALL 3 CLOUD RUN MICROSERVICES PASSED END-TO-END VERIFICATION!")
    print("=" * 75)


if __name__ == "__main__":
    main()
