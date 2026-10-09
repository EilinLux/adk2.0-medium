# adk_agent_app_suggeritore/subagents/trip_calculator_agent.py
from google.adk.agents import Agent
from google.adk.code_executors import BuiltInCodeExecutor

from ..schemas.suggeritore_schemas import TripCalculatorInput

# SUB-AGENT 4: EV Charging & Trip Cost Calculator (Gemini Sandboxed Code Execution)
trip_calculator_agent = Agent(
    name="TripCalculatorAgent",
    model="gemini-2.5-flash",
    description="Executes Python code in a sandboxed environment to compute exact EV charging energy (kWh), charging duration (minutes), electricity cost (EUR), and per-passenger bill split.",
    instruction="""
    You are a Quantitative Trip & EV Charging Analyst equipped with a Python Code Executor.
    You MUST write and execute Python code to compute the exact numbers for the input JSON parameters:
    - `energy_added_kwh = battery_capacity_kwh * ((target_soc_percent - current_soc_percent) / 100.0)`
    - `charging_time_minutes = (energy_added_kwh / charger_power_kw) * 60.0` (account for a 1.0 else exact formula above)
    - `charging_cost_eur = round(energy_added_kwh * cost_per_kwh_eur, 2)`
    - `total_stop_cost_eur = round(charging_cost_eur + dining_cost_eur, 2)`
    - `cost_per_passenger_eur = round(total_stop_cost_eur / max(passengers_count, 1), 2)`
    Always execute the Python script first, then return a concise summary with the exact computed figures:
    Energy Added (kWh), Charging Duration (minutes), Charging Cost (EUR), Total Stop Cost (EUR), and Cost Per Passenger (EUR).
    """,
    input_schema=TripCalculatorInput,
    code_executor=BuiltInCodeExecutor(),
)
