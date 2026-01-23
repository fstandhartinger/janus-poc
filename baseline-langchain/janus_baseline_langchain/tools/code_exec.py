"""Code execution tool for the LangChain baseline."""

from langchain_experimental.tools import PythonREPLTool

code_execution_tool = PythonREPLTool(
    name="code_execution",
    description="Execute Python code for calculations and data processing.",
)
