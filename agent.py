import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub

# --- Using Absolute Imports ---
# This ensures that Python can correctly locate the tool modules when
# the project is run as a package.
from bill_splitter_agent.tools.bill_calculator import bill_calculator_tool, arnona_calculator_tool
from bill_splitter_agent.tools.file_processors import pdf_reader_tool, meter_reader_tool
from bill_splitter_agent.tools.memory import get_previous_reading_tool, save_current_reading_tool

# Load the API key from the .env file
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def create_bill_splitter_agent():
    """
    Creates and configures the bill splitting agent.
    """
    # 1. Initialize the Language Model
    # The model name has been updated to a current, supported version.
    # "gemini-pro" is deprecated.
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-latest",
        google_api_key=GOOGLE_API_KEY,
        temperature=0,
        convert_system_message_to_human=True
    )

    # 2. Define the list of tools the agent can use
    tools = [
        bill_calculator_tool,
        arnona_calculator_tool,
        pdf_reader_tool,
        meter_reader_tool,
        get_previous_reading_tool,
        save_current_reading_tool
    ]

    # 3. Pull the official, known-good ReAct prompt from the LangChain Hub.
    # This is a robust way to ensure the prompt is correctly formatted and
    # contains all the required variables for the create_react_agent function.
    prompt = hub.pull("hwchase17/react")

    # 4. Create the Agent
    # This function binds the language model, tools, and prompt together
    # into a coherent reasoning engine.
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=prompt
    )

    # 5. Create the Agent Executor
    # The executor is the runtime environment that actually runs the agent,
    # calling the tools and feeding the results back into the agent's logic loop.
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True, # Set to True to see the agent's thought process in the console
        handle_parsing_errors=True,
        max_iterations=10
    )

    return agent_executor

