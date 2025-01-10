import gradio as gr
import zipfile
import os
import shutil
import subprocess
from chat_with_project import query_project
from get_prompts import get_prompt_for_mode
from dotenv import load_dotenv, set_key

# --- Configuration and Setup ---

# Define paths for workspace and extraction directories
WORKSPACE_DIR = "workspace"
EXTRACTION_DIR = "extraction"

# Create directories if they don't exist
os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(EXTRACTION_DIR, exist_ok=True)

# --- API Key Management ---

def ensure_env_file_exists():
    """Ensures that a .env file exists in the project root."""
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("")  # Create an empty .env file

def load_api_key():
    """Loads the API key from the .env file or the environment."""
    ensure_env_file_exists()
    load_dotenv()
    return os.environ.get("OPENAI_API_KEY")

def update_api_key(api_key):
    """Updates the API key in the .env file."""
    if api_key:
        set_key(".env", "OPENAI_API_KEY", api_key)
        load_dotenv()  # Reload environment variables
        return "API key updated successfully."
    else:
        return "API key cannot be empty."

def is_api_key_set():
    """Checks if the API key is set."""
    return bool(load_api_key())

# --- Core Functionalities ---

def process_zip(zip_file_path):
    """Extracts a zip file, analyzes content, and stores information."""
    try:
        # Clear and recreate the workspace directory
        shutil.rmtree(WORKSPACE_DIR, ignore_errors=True)
        os.makedirs(WORKSPACE_DIR)

        # Extract the zip file
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(WORKSPACE_DIR)

        # Run extract.py
        subprocess.run(["python", "./utils/extract.py", WORKSPACE_DIR], check=True)

        return "Processing complete! Results saved in the 'extraction' directory."

    except Exception as e:
        return f"An error occurred: {e}"

def init_milvus():
    """Initializes or loads the Milvus vector database."""
    try:
        # Run milvus.py to initialize Milvus
        result = subprocess.run(["python", "milvus.py"], capture_output=True, text=True, check=False)

        if result.returncode != 0:
            # Milvus initialization failed
            return f"Error initializing Milvus: {result.stderr}"
        else:
            # Milvus initialization successful
            return "Milvus database initialized or loaded successfully."
    except Exception as e:
        return f"Error initializing Milvus: {e}"

# --- Gradio UI Components ---

# Chat Interface
def chat_ui(query, history, mode):
    """Handles the chat interaction for Analyzer, Debugger and Developer modes."""
    api_key = load_api_key()
    if not api_key:
        return "Error: OpenAI API key not set. Please set the API key in the Settings tab.", history

    # Initialize history if None
    if history is None:
        history = []

    print(f"Chat Mode: {mode}")
    system_prompt = get_prompt_for_mode(mode)
    print(f"System Prompt: {system_prompt}")

    # Pass the query and system prompt to the LLM
    response = query_project(query, system_prompt)
    print(f"Response from query_project: {response}")

    if response is None or not response.strip():
        response = "An error occurred during processing. Please check the logs."
    
    if mode == "developer":
        extracted_files = extract_files_from_response(response)
        response_to_display = ""

        for filepath, content in extracted_files.items():
            response_to_display += f"## {filepath}\n\n`\n{content}\n`\n\n"
    else:
        response_to_display = response

    # Append user query and LLM response to history
    history.append((query, response_to_display))
    return history, history  # Returning updated history for both chatbot display and state

def extract_files_from_response(response):
    """
    Parses the LLM response to extract file paths and their corresponding code content.

    Args:
        response (str): The raw response string from the LLM.

    Returns:
        dict: A dictionary where keys are file paths and values are the code content of each file.
    """
    files = {}
    current_file = None
    current_content = []

    for line in response.splitlines():
        if line.startswith("--- BEGIN FILE:"):
            if current_file is not None:
                # Save previous file content
                files[current_file] = "\n".join(current_content)
            
            # Start a new file
            current_file = line.replace("--- BEGIN FILE:", "").strip()
            current_content = []
        elif line.startswith("--- END FILE:"):
            if current_file is not None:
                # Save current file content
                files[current_file] = "\n".join(current_content)
                current_file = None
                current_content = []
        elif current_file is not None:
            # Append line to current file content
            current_content.append(line)

    return files

# ZIP Processing Interface
zip_iface = gr.Interface(
    fn=process_zip,
    inputs=gr.File(label="Upload ZIP File"),
    outputs="text",
    title="Zip File Analyzer",
    description="Upload a zip file to analyze and store its contents.",
)

# Milvus Initialization Interface
milvus_iface = gr.Interface(
    fn=init_milvus,
    inputs=None,
    outputs="text",
    title="Milvus Database Initialization",
    description="Initialize or load the Milvus vector database.",
)

# Gradio Chatbot UI Interface
chat_iface = gr.Interface(
    fn=chat_ui,
    inputs=[
        gr.Textbox(label="Ask a question", placeholder="Type your question here"),
        gr.State(),  # Maintains chat history
        gr.Radio(["analyzer", "debugger", "developer"], label="Chat Mode", value="analyzer")
    ],
    outputs=[
        gr.Chatbot(label="Chat with Project"),
        "state"
    ],
    title="Chat with your Project",
    description="Ask questions about the data extracted from the zip file.",
    examples=[["What is this project about?"], ["Are there any potential bugs?"],
              ["How does the data flow through the application?"],
              ["Explain the main components of the architecture."],
              ["What are the dependencies of this project?"],
              ["Are there any potential memory leaks?"],
              ["Identify any areas where the code could be optimized."],
              ["Is there any error handling missing in this function?"],
              ["Add a new endpoint to list all users to the server.py file"]
              ],
)

# Settings Interface
settings_iface = gr.Interface(
    fn=update_api_key,
    inputs=gr.Textbox(label="OpenAI API Key", type="password"),
    outputs="text",
    title="Settings",
    description="Set your OpenAI API key.",
)

# Status Interface
def get_api_key_status():
    if is_api_key_set():
        return "API key status: Set"
    else:
        return "API key status: Not set"

status_iface = gr.Interface(
    fn=get_api_key_status,
    inputs=None,
    outputs="text",
    live=True,
    title="API Key Status"
)

# Add credits to the UI
credits = gr.Markdown("## Credits\n\nCreated by [Ruslan Magana Vsevolodovna](https://ruslanmv.com/)")

# --- Main Application Launch ---

# Combine the interfaces using Tabs
demo = gr.TabbedInterface(
    [zip_iface, milvus_iface, chat_iface, settings_iface, status_iface],
    ["Process ZIP", "Init Milvus", "Chat with Project", "Settings", "Status"],
)

# Launch the app with credits
demo.queue().launch()