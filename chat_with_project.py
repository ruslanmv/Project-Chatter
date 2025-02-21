from pymilvus import connections, Collection, utility
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI  # Updated import
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import os

# Milvus connection details
MILVUS_HOST = 'localhost'
MILVUS_PORT = '19530'
COLLECTION_NAME = 'document_collection'

def load_api_key():
    """Loads the API key from the .env file or the environment."""
    from dotenv import load_dotenv
    load_dotenv()
    return os.environ.get("OPENAI_API_KEY")

# Embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

def retrieve_relevant_documents(query, top_k=5):
    """
    Retrieves the most relevant documents from Milvus based on the query.
    """
    print(f"Connecting to Milvus at {MILVUS_HOST}:{MILVUS_PORT}...")
    connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
    if utility.has_collection(COLLECTION_NAME):
        collection = Collection(COLLECTION_NAME)
        collection.load()

        query_vector = model.encode([query]).tolist()
        print(f"Encoded Query Vector: {query_vector}")

        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 16}
        }
        search_results = collection.search(
            data=query_vector,
            anns_field="content_vector",
            param=search_params,
            limit=top_k,
            expr=None,
            output_fields=["path"]
        )

        relevant_docs = []
        for hit in search_results[0]:
            doc_path = hit.entity.get("path")
            relevant_docs.append(doc_path)

        print(f"Relevant Docs: {relevant_docs}")
        connections.disconnect(alias='default')
    else:
        print(f"Collection {COLLECTION_NAME} does not exist.")
        relevant_docs = []

    return relevant_docs


def generate_response_with_gpt(query, relevant_docs, system_prompt):
    """
    Generates a response using OpenAI's GPT model, based on the query, relevant documents, and system prompt.
    """
    api_key = load_api_key()
    if not api_key:
        raise ValueError("OpenAI API key not set. Please set it in the .env file or environment variables.")

    print(f"Using OpenAI API Key: {api_key[:5]}...")  # Partial key for debugging
    chat = ChatOpenAI(temperature=0.7, openai_api_key=api_key, model_name="gpt-3.5-turbo")

    messages = [SystemMessage(content=system_prompt)]
    if relevant_docs:
        doc_content = ""
        for doc_path in relevant_docs:
            if os.path.isfile(doc_path):
                try:
                    with open(doc_path, "r", encoding="utf-8") as f:
                        doc_content += f.read() + "\n"
                except Exception as e:
                    print(f"Error reading document {doc_path}: {e}")
        if doc_content:
            messages.append(HumanMessage(content=f"Relevant documents:\n{doc_content}"))

    messages.append(HumanMessage(content=query))
    print(f"Messages sent to OpenAI API: {messages}")

    try:
        response = chat.invoke(messages)
        print(f"OpenAI API Response: {response.content}")
        print("Type OpenAI API Response",type(response.content))
        return response.content
    except Exception as e:
        print(f"Error during OpenAI API call: {e}")
        return "Error generating response. Please try again later."


def query_project(query, system_prompt):
    """
    Queries the project using a RAG approach with specified system prompt.
    """
    relevant_docs = retrieve_relevant_documents(query)
    print(" Starting the query:")
    print(query)
    response = generate_response_with_gpt(query, relevant_docs, system_prompt)
    print(f"Query Response: {response}")
    print("Type response",type(response))
    return response