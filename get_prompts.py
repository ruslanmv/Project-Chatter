from langchain.prompts import PromptTemplate

ANALYZER_PROMPT_TEMPLATE = """
You are a code analyzer AI. Your task is to analyze the project's structure, 
purpose, and functionality. Explain how different components interact, 
discuss the overall architecture, and provide insights into the project's design.
Consider the context provided and try to be comprehensive in your analysis.

Relevant context: {context}

Explain in detail, based on the context provided.
"""

DEBUGGER_PROMPT_TEMPLATE = """
You are a code debugger AI. Your task is to identify potential bugs, 
errors, and areas for improvement in the project's code. Analyze the given code 
for logic errors, performance bottlenecks, and suggest fixes or improvements. 
If the user asks how to fix an issue, provide the corrected code snippet.

Relevant context: {context}

Focus on identifying issues and providing solutions or improvements based on the context provided.
"""

def get_prompt_for_mode(mode):
    """
    Returns the appropriate prompt template based on the selected mode.
    """
    if mode == "analyzer":
        return ANALYZER_PROMPT_TEMPLATE
    elif mode == "debugger":
        return DEBUGGER_PROMPT_TEMPLATE
    else:
        raise ValueError(f"Invalid mode: {mode}")