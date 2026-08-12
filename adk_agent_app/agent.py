# adk_agent_app/agent.py
import os
import sys

from google.adk.agents import Agent

from .subagents.cameriere_agent import cameriere_agent
from .subagents.registratore_agent import registratore_agent
from .test_connections import run_all_tests
from .tools.gatekeeper_tools import is_registered_user_tool

# 1. Execute infrastructure pre-flight check before agent startup (can be skipped on Cloud Run cold start)
if os.getenv("SKIP_PREFLIGHT_CHECKS", "").lower() != "true":
    print("\n🔍 Running infrastructure pre-flight checks...")
    if not run_all_tests():
        print("❌ Pre-flight checks failed! Halting agent startup.")
        sys.exit(1)

root_agent = Agent(
    name="Gatekeeper",
    model="gemini-2.5-flash",
    description="Root agent for the Sosta app",
    instruction="""
    You are the welcoming Gatekeeper of the Sosta app. 
    
    1. Greet the user politely and ask if they are already registered.
    2. IF YES: Ask for their User ID and use 'is_registered_user' to check it.
       - If it exists, transfer them to the 'Cameriere'.
       - If not, inform them there was an error and ask to try again.
    3. IF NO: Ask if they want to register.
       - If yes, transfer them to the 'Registratore'.
       - If no, politely say goodbye and end the conversation.
    """,
    tools=[is_registered_user_tool],
    sub_agents=[registratore_agent, cameriere_agent],
)