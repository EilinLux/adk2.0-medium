# tests/07a-tool-caching-and-session-scaling/test_terraform_redis.py
"""Test Terraform configuration for Cloud Memorystore Redis and tool caching infrastructure."""

from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TERRAFORM_DIR = REPO_ROOT / "terraform" / "terraform_infrastructure"


def test_redis_tf_exists_and_configured():
    redis_file = TERRAFORM_DIR / "redis.tf"
    assert redis_file.exists(), "redis.tf must exist in terraform/terraform_infrastructure"

    content = redis_file.read_text()
    assert "google_redis_instance" in content
    assert "var.enable_memorystore_redis" in content
    assert "var.redis_tier" in content
    assert "var.redis_memory_size_gb" in content
    assert "redis_version" in content
    assert "REDIS_7_0" in content


def test_variables_tf_contains_redis_variables():
    vars_file = TERRAFORM_DIR / "variables.tf"
    content = vars_file.read_text()

    assert 'variable "enable_memorystore_redis"' in content
    assert 'variable "redis_tier"' in content
    assert 'variable "redis_memory_size_gb"' in content
    assert 'default     = false' in content  # Off by default for cost optimization


def test_outputs_tf_contains_redis_outputs():
    outputs_file = TERRAFORM_DIR / "outputs.tf"
    content = outputs_file.read_text()

    assert 'output "redis_host"' in content
    assert 'output "redis_port"' in content


def test_locals_tf_enables_redis_api():
    locals_file = TERRAFORM_DIR / "locals.tf"
    content = locals_file.read_text()

    assert '"redis.googleapis.com"' in content
