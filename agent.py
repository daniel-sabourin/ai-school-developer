import os
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import tool
from langsmith import traceable
from langchain_community.tools.shell.tool import ShellTool
from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
import subprocess
from typing import Optional

ROOT_DIR = "./"

@tool
def create_react_app_with_vite():
    """
    Creates a new React application using Vite in the 'app' directory.

    It navigates to the root directory, creates a new directory named 'app',
    and used the npm 'create vite@latest' command to create a new React app.
    If the process is successful, it returns a success message.
    If the process fails, it returns an error message.
    """
    try:
        subprocess.run(["npm", "create", "vite@latest", ".", "--template" "react"], check=True)
        return "React app created with Vite in the 'app' directory."
    except subprocess.CalledProcessError as e:
        return f"Error creating React app with Vite: {e}"
    except Exception as e:
        return f"Error creating React app with Vite: {str(e)}"

@tool
def create_directory(directory: str) -> str:
    """
    Creates a new writable directory with the given name if it does not exist.
    If the directory already exists, it ensures the directory is writable.

    Parameters:
    directory (str): The name of the directory to create.

    Returns:
    str: Success or error message.
    """

    # TODO fix double filename issue
    if ".." in directory:
        return "Error: Unable to make directory with '..' in the name."
    try:
        if not os.path.exists(directory):
            subprocess.run(["mkdir", "-p", directory], check=True)
            subprocess.run(["chmod", "u+w", directory], check=True)
            return f"Directory '{directory}' created and set as writeable."
        else:
            subprocess.run(["chmod", "u+w", directory], check=True)
            return f"Directory '{directory}' already exists and was made writable."
    except Exception as e:
        return f"Error creating directory '{directory}': {e}"

@tool
def find_file(filename: str, path: str) -> Optional[str]:
    """
    Recursively searches for a file in the given path.
    Returns string of full path to file, or None if file not found.
    """
    # TODO handle multiple matches
    for root, dirs, files in os.walk(path):
        if filename in files:
            return os.path.join(root, filename)

    return None

@tool
def create_file(filename: str, content: str = "", directory="", file_type: str = ""):
    """Creates a new file with specified file type and content in the specified directory."""

    valid_file_types = {".txt", ".js", ".html", ".css", ".json", ".md", ".py", ".png"}
    # if file_type[0] != ".":
    #     file_type = f".{file_type}"
    if file_type not in valid_file_types:
        print(f"Error: Invalid file type '{file_type}'. Supported types: {valid_file_types}")
        return f"Error: Invalid file type '{file_type}'. Supported types: {valid_file_types}"

    filename += file_type
    directory_path = os.path.join(ROOT_DIR, directory)
    file_path = os.path.join(directory_path, filename)
    if not os.path.exists(file_path):
        try:
            with open(file_path, "w") as file:
                file.write(content)
            print(f"File '{filename}' created in directory '{directory}'.")
            return f"File '{filename}' created in directory '{directory}'."
        except Exception as e:
            return f"Error creating file '{filename}': {str(e)}"
    else:
        print(f"Error: File '{filename}' already exists in directory '{directory}'.")
        return f"Error: File '{filename}' already exists in directory '{directory}'."

@tool
def update_file(filename: str, content: str, directory: str = ""):
    """Updates, appends, or modifies an existing file with new content."""
    if directory:
        file_path = os.path.join(ROOT_DIR, directory, filename)
    else:
        file_path = find_file(filename, ROOT_DIR)

    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "a") as file:
                file.write(content)
            print(f"Content added to file '{filename}'.")
            return f"Content added to file '{filename}'."
        except Exception as e:
            print(f"Error updating file '{filename}': {str(e)}")
            return f"Error updating file '{filename}': {str(e)}"
    else:
        print(f"Error: File '{filename}' not found.")
        return f"Error: File '{filename}' not found."

# List of tools to use
tools = [
    ShellTool(ask_human_input=True),
    create_directory,
    # create_react_app_with_vite,
    find_file,
    create_file,
    update_file
    # Add more tools if needed
]

# Configure the language model
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# Set up the prompt template
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert web developer.",
        ),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

# Bind the tools to the language model
llm_with_tools = llm.bind_tools(tools)

# Create the agent
agent = (
    {
        "input": lambda x: x["input"],
        "agent_scratchpad": lambda x: format_to_openai_tool_messages(
            x["intermediate_steps"]
        ),
    }
    | prompt
    | llm_with_tools
    | OpenAIToolsAgentOutputParser()
)

agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Create the agent executor
agent_executor = (
    # Fill in the code to create the agent executor here
    AgentExecutor(agent=agent, tools=tools, verbose=True)
)

# Main loop to prompt the user
while True:
    user_prompt = input("Prompt: ")
    list(agent_executor.stream({"input": user_prompt}))
