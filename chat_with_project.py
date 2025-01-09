from pymilvus import connections, Collection
import openai
from sentence_transformers import SentenceTransformer
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage

# Milvus connection details
MILVUS_HOST = 'localhost'
MILVUS_PORT = '19530'
COLLECTION_NAME = 'document_collection'

# OpenAI API Key 
openai.api_key = os.environ.get("OPENAI_API_KEY")
if openai.api_key is None:
    raise ValueError("Please set your OpenAI API key in the environment variable OPENAI_API_KEY.")

# Embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

def retrieve_relevant_documents(query, top_k=5):
    """
    Retrieves the most relevant documents from Milvus based on the query.
    """
    connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
    collection = Collection(COLLECTION_NAME)
    collection.load()

    query_vector = model.encode([query]).tolist()
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

    connections.disconnect(alias='default')
    return relevant_docs

def generate_response_with_gpt(query, relevant_docs, system_prompt):
    """
    Generates a response using OpenAI's GPT model, based on the query, relevant documents, and system prompt.
    """
    chat = ChatOpenAI(temperature=0.7, openai_api_key=openai.api_key, model_name="gpt-3.5-turbo")

    messages = [
        SystemMessage(content=system_prompt),
    ]

    # Add relevant documents to the context
    if relevant_docs:
        doc_content = ""
        for doc_path in relevant_docs:
            try:
                with open(doc_path, 'r', encoding='utf-8') as f:
                    doc_content += f.read() + "\n"
            except Exception as e:
                print(f"Error reading document {doc_path}: {e}")
        messages.append(HumanMessage(content=f"Relevant documents:\n{doc_content}"))

    messages.append(HumanMessage(content=query))
    response = chat(messages)
    return response.content

def query_project(query, system_prompt):
    """
    Queries the project using a RAG approach with specified system prompt.
    """
    relevant_docs = retrieve_relevant_documents(query)
    response = generate_response_with_gpt(query, relevant_docs, system_prompt)
    return response