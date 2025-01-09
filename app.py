import gradio as gr
import zipfile
import os
import shutil
import subprocess
from chat_with_project import query_project
from get_prompts import get_prompt_for_mode
from dotenv import load_dotenv, dotenv_values, set_key

# Load initial environment variables from .env file
load_dotenv()

# Ensure the 'workspace' and 'extraction' directories exist
WORKSPACE_DIR = "workspace"
EXTRACTION_DIR = "extraction"
if not os.path.exists(WORKSPACE_DIR):
    os.makedirs(WORKSPACE_DIR)
if not os.path.exists(EXTRACTION_DIR):
    os.makedirs(EXTRACTION_DIR)

# Function to update API key in .env file
def update_api_key(api_key):
    env_file = ".env"
    if api_key:
        set_key(env_file, "OPENAI_API_KEY", api_key)
        load_dotenv()  # Reload environment variables
        return "API key updated successfully."
    else:
        return "API key cannot be empty."

# Function to check if the API key is set
def is_api_key_set():
    return "OPENAI_API_KEY" in dotenv_values() and dotenv_values()["OPENAI_API_KEY"] != ""

def process_zip(zip_file_path):
    """
    Extracts a zip file, analyzes content, and stores information.
    """
    try:
        # Clear and recreate the workspace directory
        if os.path.exists(WORKSPACE_DIR):
            shutil.rmtree(WORKSPACE_DIR)
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
    """
    Initializes or loads the Milvus vector database.
    """
    try:
        # Run milvus.py to initialize Milvus
        subprocess.run(["python", "milvus.py"], check=True)
        return "Milvus database initialized or loaded successfully."
    except Exception as e:
        return f"Error initializing Milvus: {e}"

# Gradio UI components
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
    """
    Handles the chat interaction for both Analyzer and Debugger modes.
    """
    if not is_api_key_set():
        return "Error: OpenAI API key not set. Please set the API key in the Settings tab.", history

    system_prompt = get_prompt_for_mode(mode)
    response = query_project(query, system_prompt)

    # Update history for UI display
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
    live=True,  # This makes the interface update automatically
    title="API Key Status"
)
# Add credits to the UI
credits = gr.Markdown("## Credits\n\nCreated by [Ruslan Mavlyutov](https://ruslanmv.com/)")

# Combine the interfaces using Tabs
demo = gr.TabbedInterface(
    [zip_iface, milvus_iface, chat_iface, settings_iface, status_iface],
    ["Process ZIP", "Init Milvus", "Chat with Project", "Settings", "Status"],
)

# Launch the app with credits
demo.queue().launch()