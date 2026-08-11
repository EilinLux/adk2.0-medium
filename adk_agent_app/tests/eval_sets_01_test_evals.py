# tests/test_agent_evaluations.py
import asyncio
import importlib
import os
import sys
from pathlib import Path
import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator, EvalConfig

# Ensure project root is in sys.path for relative module loading
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
@pytest.mark.asyncio

async def test_existing_user_preference_update():
    """
    Multi-turn Evaluation:
    Validates that Gatekeeper verifies user 'usr_0a8f67', transfers to Cameriere,
    and updates user dietary preferences (adding oysters for a previously vegan profile).
    """
    module_name = "adk_agent_app.agent"
    
    # 1. Dynamically import the target agent module
    try:
        agent_module = importlib.import_module(module_name)
    except ImportError:
        sys.path.append(os.getcwd())
        agent_module = importlib.import_module(module_name)
        
    # 2. Reset mock data to ensure a clean slate
    if hasattr(agent_module, "reset_mock_data"):
        agent_module.reset_mock_data()
    # 3. Use absolute path to the eval file to remain robust to execution context
    script_dir = Path(__file__).parent.resolve()
    eval_file = script_dir.parent / "evals" / "eval_set_1a_new_user.evalset.json"
    # 4. Await AgentEvaluator.evaluate (ADK 2.0 evaluate is an async coroutine)
    await AgentEvaluator().evaluate(
        agent_module=module_name,
        eval_dataset_file_path_or_dir=str(eval_file),
        num_runs=1,
        print_detailed_results=True,


    )



@pytest.mark.asyncio
async def test_single_turn_tool_trajectories():
    """Single-turn: Ensures root agent executes 'is_registered_user' correctly."""
    script_dir = Path(__file__).parent.resolve()
    eval_file = script_dir.parent / "evals" / "eval_set_1a_new_user.evalset.json"
    await AgentEvaluator.evaluate(
        agent_module="adk_agent_app.agent",
        eval_dataset_file_path_or_dir=str(eval_file),
        num_runs=1,
        print_detailed_results=True,
    )