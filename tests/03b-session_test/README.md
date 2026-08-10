1. session_test_1_output_key.py (Without output_schema)
Because no structured output schema was enforced on the agent, the LLM generated free-form conversational text (along with a tool call string) and ADK captured the entire raw text response string and dumped it as a plain string directly into session.state["preferences"]:
{
  'user_preferred_language': 'Italian', 
  'registered_user': True, 
  'current_subagent': 'gatekeeper_agent', 
  'preferences': "_set_session_state(preference_favorite_dish='Risotto Alla Milanese')\nThank you! I've noted that your favorite dish is Risotto Alla Milanese."
}  
The Problem is that it pollutes your state with conversational filler and formatting fluff, making it messy and difficult for downstream tools or other agents to query programmatically.
2. session_test_2_output_key_with_output_schema.py (With output_schema)

By providing an output_schema (a Pydantic model defining key and value), you forced the LLM to output clean, strictly validated JSON conforming to that schema, so that ADK parsed that JSON and saved it as a clean, structured Python dictionary inside session.state["preferences"]:
'preferences': {'key': 'preference_favorite_dish', 'value': 'Risotto Alla Milanese'}
The stored data is type-safe, predictable, and immediately accessible via key-value access (session.state["preferences"]["value"]) without needing string parsing or regex.