import gradio as gr
import zipfile
import os
import shutil
import subprocess
from chat_with_project import query_project
from get_prompts import get_prompt_for_mode
from dotenv import load_dotenv, dotenv_values, set_key

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
    env_file_path = ".env"
    if not os.path.exists(env_file_path):
        with open(env_file_path, "w") as f:
            f.write("")  # Create an empty .env file

def load_api_key():
    """Loads the API key from the .env file or the environment."""
    ensure_env_file_exists()
    load_dotenv()
    return os.environ.get("OPENAI_API_KEY")

def update_api_key(api_key):
    """Updates the API key in the .env file."""
    env_file = ".env"
    if api_key:
        set_key(env_file, "OPENAI_API_KEY", api_key)
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

# Chat Interface
def chat_ui(query, history, mode):
    """Handles the chat interaction for both Analyzer and Debugger modes."""
    api_key = load_api_key()
    if not api_key:
        return "Error: OpenAI API key not set. Please set the API key in the Settings tab.", history

    # Initialize history if None
    if history is None:
        history = []

    print(f"Chat Mode: {mode}")
    system_prompt = get_prompt_for_mode(mode)
    print(f"System Prompt: {system_prompt}")

    # Pass the history to query_project
    response = query_project(query, system_prompt)
    print(f"Response from query_project: {response}")

    if response is None:
        response = "An error occurred during processing. Please check the logs."

    history.append((query, response))
    return "", history
# Gradio Chatbot UI
chatbot = gr.Chatbot(
    [],
    elem_id="chatbot",
    bubble_full_width=False,
    avatar_images=(None, (os.path.join(os.path.dirname(__file__), "deriv_logo.png"))),
)

chat_iface = gr.Interface(
    fn=chat_ui,
    inputs=[
        "text",
        "state",
        gr.Radio(["analyzer", "debugger"], label="Chat Mode", value="analyzer")
    ],
    outputs=["text", "state"],
    title="Chat with your Project",
    description="Ask questions about the data extracted from the zip file.",
    examples=[["What is this project about?"], ["Are there any potential bugs?"]],
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