from pymongo import MongoClient
import os

# Nice way to load environment variables for deployments
from dotenv import load_dotenv
load_dotenv()

# Find out what vector provider we're using so we can load the right libraries
provider = os.environ["PROVIDER"]

# OpenAI Stuff
if provider == "openai":
    from openai import OpenAI
    oai_client = OpenAI(api_key=os.environ["OPENAI_KEY"])
elif provider == "vectorservice":
    import requests
elif provider == "mistral":
    from mistralai.client import MistralClient
    mistral_client = MistralClient(api_key=os.environ["MISTRAL_API_KEY"])

# Set up your MongoDB connection and specify collection and inputs/outputs 
# Loads from .env file or environment variables
client = MongoClient( os.environ["MONGO_CON"])
db = client[os.environ["MONGO_DB"]]
collection = db[os.environ["MONGO_COL"]]
input_field = os.environ["INPUT_FIELD"]
output_field = os.environ["OUTPUT_FIELD"]
provider = os.environ["PROVIDER"]

# Initialize the change stream
change_stream = collection.watch([], full_document='updateLookup')

# Function to get embeddings from a VectorService endpoint  
def get_embedding_VectorService(embed_text):
    response = requests.get(os.environ["VECTOR_SERVICE_URL"], params={"text":embed_text }, headers={"accept": "application/json"})
    vector_embedding = response.json()
    return vector_embedding

# Function to get embeddings from OpenAI
def get_embedding_OpenAI(text):
   text = text.replace("\n", " ")
   vector_embedding = oai_client.embeddings.create(input = [text], model="text-embedding-ada-002").data[0].embedding
   return vector_embedding

# Function to get embeddings from Mistral
def get_embedding_Mistral(text):
    vector_embedding = mistral_client.embeddings(model="mistral-embed", input=[text]).data[0].embedding
    return vector_embedding

# Providing multiple embedding services depending on config
def get_embedding(text):
    if provider == "openai":
        return get_embedding_OpenAI(text)
    elif provider == "vectorservice":
        return get_embedding_VectorService(text)
    elif provider == "mistral":
        return get_embedding_Mistral(text)

# Function to populate all the initial embeddings by detecting any fields with missing embeddings
def initial_sync():
    # We only care about documents with missing keys
    query = {output_field: {"$exists": False}} 
    results = collection.find(query)

    # Every document gets a new embedding
    total_records = 0
    for result in results:
        total_records = total_records + 1
        embed_text = result[input_field]
        vector_embedding = get_embedding(embed_text)

        # Store the vector embeddings back into collection
        collection.update_one({'_id': result["_id"]},{"$set": {output_field: vector_embedding}})
    return total_records

# Function to handle changes in the collection
def handle_changes(change):
    # Extract the necessary information from the change document
    operation_type = change['operationType']

    # Bail out if the detected update is the embedding we just did!
    if operation_type == "update" and output_field in change['updateDescription']['updatedFields']:
        return

    # Anytime we create, update or replace documents, the embedding needs to be updated
    if operation_type == "replace" or operation_type == "update" or operation_type == "insert":
        # Get the _id for update later and our input field to vectorize
        document_key = change['fullDocument']['_id']
        embed_text = change['fullDocument'][input_field]
        vector_embedding = get_embedding_VectorService(embed_text)
        
        # Store the vector embeddings back into collection
        collection.update_one({'_id': document_key},{"$set": {output_field: vector_embedding}})

# Perform initial sync
print(f"Initial sync for {db.name} db and {collection.name} collection. Watching for changes to {input_field} and writing to {output_field}...")
total_records = initial_sync()
print(f"Sync complete {total_records} missing embeddings")
print(f"Change stream active...")

# Start consuming changes from the change stream
for change in change_stream:
    handle_changes(change)