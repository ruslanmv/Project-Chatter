from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
import pandas as pd
import os
import sys
from sentence_transformers import SentenceTransformer
import time

# Milvus connection details (adjust if needed)
MILVUS_HOST = 'localhost'
MILVUS_PORT = '19530'
COLLECTION_NAME = 'document_collection'
DIMENSION = 384  # Adjust based on your embedding model
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

def create_milvus_collection():
    """
    Creates a new Milvus collection if it doesn't exist.
    """
    if not utility.has_collection(COLLECTION_NAME):
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="path", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="content_vector", dtype=DataType.FLOAT_VECTOR, dim=DIMENSION)
        ]
        schema = CollectionSchema(fields, "Document Vector Store")
        collection = Collection(COLLECTION_NAME, schema)

        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        collection.create_index(field_name="content_vector", index_params=index_params)
        print(f"Collection {COLLECTION_NAME} created and index built.")
    else:
        print(f"Collection {COLLECTION_NAME} already exists.")

def load_data_to_milvus():
    """
    Loads data from the DataFrame into Milvus, using sentence embeddings.
    """
    extraction_dir = "extraction"
    pkl_files = [f for f in os.listdir(extraction_dir) if f.endswith('.pkl')]
    if not pkl_files:
        print("No .pkl files found in the 'extraction' directory.")
        return

    df_path = os.path.join(extraction_dir, pkl_files[0])
    df = pd.read_pickle(df_path)

    # Generate sentence embeddings
    df['content_vector'] = df['content'].apply(lambda x: model.encode(x).tolist())

    data_to_insert = [
        df['path'].tolist(),
        df['content_vector'].tolist()
    ]

    collection = Collection(COLLECTION_NAME)
    collection.insert(data_to_insert)
    collection.flush()

    print(f"Data from {df_path} loaded into Milvus collection {COLLECTION_NAME}.")

if __name__ == "__main__":
    retries = 0
    while retries < MAX_RETRIES:
        try:
            connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
            create_milvus_collection()
            load_data_to_milvus()
            connections.disconnect(alias='default')
            break  # Connection successful, break out of the loop
        except Exception as e:
            print(f"Error connecting to Milvus: {e}")
            retries += 1
            if retries < MAX_RETRIES:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                print("Max retries reached. Could not connect to Milvus.")
                sys.exit(1)  # Exit with an error code