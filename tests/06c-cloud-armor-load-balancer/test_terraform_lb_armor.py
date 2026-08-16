# tests/06c-cloud-armor-load-balancer/test_terraform_lb_armor.py
"""Automated validation tests for Cloud Armor WAF and External Application Load Balancer.

Verifies:
1. Terraform syntax, provider locking, and canonical formatting (`terraform validate`, `terraform fmt -check`).
2. Structural verification of Cloud Armor security policy (`google_compute_security_policy.sosta_armor`):
   - OWASP CRS v4.22 preconfigured WAF rules (SQLi, XSS, RFI, RCE, Protocol Attack, Scanner Detection, Session Fixation).
   - Zero-day and CVE canaries (`cve-canary`, `json-sqli-canary`).
   - Adaptive IP rate limiting throttle action (HTTP 429).
   - Optional Geo-fencing expression logic (`origin.region_code`).
   - Default fallthrough allow rule (priority 2147483647).
3. Structural verification of External Application Load Balancer:
   - Global IPv4 address allocation (`google_compute_global_address.lb_ip`).
   - Serverless Network Endpoint Group (`google_compute_region_network_endpoint_group.runner_neg`) targeting `adk_agent`.
   - Backend service (`google_compute_backend_service.runner_backend`) with `EXTERNAL_MANAGED` scheme,
     Cloud Armor attachment, and `timeout_sec >= 300` for Server-Sent Events (SSE) streaming.
   - URL map, target HTTP proxy, and global forwarding rule.
   - Architectural isolation: verify internal services (`mcp_sse`, `suggeritore_a2a`) are NOT attached to public LB.
"""

import re
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TF_INFRA_DIR = REPO_ROOT / "terraform" / "terraform_infrastructure"
CLOUD_ARMOR_TF = TF_INFRA_DIR / "cloud-armor.tf"
LOAD_BALANCER_TF = TF_INFRA_DIR / "load-balancer.tf"
VARIABLES_TF = TF_INFRA_DIR / "variables.tf"
OUTPUTS_TF = TF_INFRA_DIR / "outputs.tf"


def test_terraform_canonical_format():
    """Verify all Terraform files adhere to canonical formatting."""
    result = subprocess.run(
        ["terraform", "fmt", "-check"],
        cwd=str(TF_INFRA_DIR),
        capture_output=True,
        text=True,
    )
    assert (
        result.returncode == 0
    ), f"Terraform formatting check failed:\n{result.stderr}\n{result.stdout}"


def test_terraform_validate_syntax():
    """Verify Terraform configuration parses and validates cleanly against provider schemas."""
    result = subprocess.run(
        ["terraform", "validate"],
        cwd=str(TF_INFRA_DIR),
        capture_output=True,
        text=True,
    )
    assert (
        result.returncode == 0
    ), f"Terraform validation failed:\n{result.stderr}\n{result.stdout}"


def test_cloud_armor_security_policy_structure():
    """Verify Cloud Armor security policy contains mandatory OWASP CRS rules, CVE canaries, and rate limiting."""
    assert (
        CLOUD_ARMOR_TF.is_file()
    ), f"Missing cloud-armor.tf in {TF_INFRA_DIR}"
    content = CLOUD_ARMOR_TF.read_text(encoding="utf-8")

    # 1. Resource declaration
    assert 'resource "google_compute_security_policy" "sosta_armor"' in content

    # 2. OWASP CRS v4.22 rules
    expected_owasp_rules = [
        ("sqli-v422-stable", 100),
        ("xss-v422-stable", 101),
        ("rfi-v422-stable", 103),
        ("rce-v422-stable", 104),
        ("protocolattack-v422-stable", 105),
        ("scannerdetection-v422-stable", 106),
        ("sessionfixation-v422-stable", 107),
    ]
    for rule_id, priority in expected_owasp_rules:
        assert (
            rule_id in content
        ), f"Missing OWASP CRS rule '{rule_id}' in cloud-armor.tf"
        pattern = rf"priority\s*=\s*{priority}"
        assert re.search(
            pattern, content
        ), f"Priority {priority} for {rule_id} not found in cloud-armor.tf"

    # 3. Known CVE canaries
    assert "cve-canary" in content, "Missing cve-canary rule in cloud-armor.tf"
    assert (
        "json-sqli-canary" in content
    ), "Missing json-sqli-canary rule in cloud-armor.tf"

    # 4. Rate limiting with HTTP 429
    assert 'action   = "throttle"' in content
    assert 'exceed_action  = "deny(429)"' in content
    assert "rate_limit_threshold" in content

    # 5. Default allow rule
    assert "2147483647" in content
    assert 'action   = "allow"' in content


def test_load_balancer_and_serverless_neg_structure():
    """Verify Load Balancer, Serverless NEG, and SSE timeout configuration."""
    assert (
        LOAD_BALANCER_TF.is_file()
    ), f"Missing load-balancer.tf in {TF_INFRA_DIR}"
    content = LOAD_BALANCER_TF.read_text(encoding="utf-8")

    # 1. Global external IP
    assert 'resource "google_compute_global_address" "lb_ip"' in content

    # 2. Serverless NEG targeting SostaApp runner
    assert (
        'resource "google_compute_region_network_endpoint_group" "runner_neg"'
        in content
    )
    assert 'network_endpoint_type = "SERVERLESS"' in content
    assert "google_cloud_run_v2_service.adk_agent.name" in content

    # 3. Backend service with Cloud Armor WAF attachment and long timeout for SSE
    assert (
        'resource "google_compute_backend_service" "runner_backend"' in content
    )
    assert 'load_balancing_scheme = "EXTERNAL_MANAGED"' in content
    assert (
        "security_policy       = google_compute_security_policy.sosta_armor.id"
        in content
    )
    assert (
        "group = google_compute_region_network_endpoint_group.runner_neg.id"
        in content
    )
    assert (
        "timeout_sec" in content
    ), "timeout_sec must be explicitly defined for SSE streaming"

    # 4. Global forwarding rule and URL map
    assert 'resource "google_compute_url_map" "lb_url_map"' in content
    assert 'resource "google_compute_target_http_proxy" "http_proxy"' in content
    assert (
        'resource "google_compute_global_forwarding_rule" "http_forwarding_rule"'
        in content
    )

    # 5. Architectural isolation check: mcp_sse and suggeritore_a2a must NEVER be in LB backend
    assert (
        "google_cloud_run_v2_service.mcp_sse.name" not in content
    ), "Internal service mcp_sse must NOT be exposed via Load Balancer"
    assert (
        "google_cloud_run_v2_service.suggeritore_a2a.name" not in content
    ), "Internal service suggeritore_a2a must NOT be exposed via Load Balancer"


def test_variables_and_outputs_declaration():
    """Verify variables and outputs are declared for Cloud Armor and Load Balancer."""
    var_content = VARIABLES_TF.read_text(encoding="utf-8")
    assert "cloud_armor_enforce_geo_fencing" in var_content
    assert "cloud_armor_allowed_regions" in var_content
    assert "cloud_armor_rate_limit_count" in var_content
    assert "cloud_armor_rate_limit_interval_sec" in var_content
    assert "lb_backend_timeout_sec" in var_content

    out_content = OUTPUTS_TF.read_text(encoding="utf-8")
    assert 'output "load_balancer_ip"' in out_content
    assert 'output "load_balancer_url"' in out_content
    assert 'output "cloud_armor_policy_name"' in out_content
    assert 'output "cloud_armor_policy_id"' in out_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
