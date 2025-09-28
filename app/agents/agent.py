from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from prompts.prompts import SYSTEM_PROMPT
from tools.tools import fetch_log_file, rag_retrieve, store_final_report

# Collect registered tools
tools = [fetch_log_file, rag_retrieve, store_final_report]

# Model
model = ChatOpenAI(model="gpt-4o", temperature=0)

# Agent + executor
agent = create_react_agent(model, tools, SYSTEM_PROMPT)
agent_executor = AgentExecutor(agent=agent, tools=tools)

def run_agent(incident_json: str):
    """
    Run the ReAct agent on the given incident JSON string.
    Example input:
      '{"incident_id": "INC001", "source": "fraud-detection", "spike_percentage": 40}'
    """
    prefixed_input = (
        "These are the details regarding the incident. "
        "Investigate this issue step by step using the available tools "
        "and prepare a comprehensive incident report for the developer.\n\n"
        f"Incident details:\n{incident_json}"
    )

    return agent_executor.invoke({"input": prefixed_input})