# Vector Stream

This tool automatically fetches and updates vector embeddings for your Atlas Vector Search use cases.

* Supports OpenAI (text-ada-002), Mistral (mistral-embed) and VectorService (https://github.com/patw/VectorService)
* Configure the .env file to point to your atlas instance, database, collection and which field to vectorize and which field to store the embedding
* Configure optional OpenAI or Mistral keys for hosted services
* Automatically performs embedding for all records with missing keys
* Listens to changestreams for insert, replace and update events.  Calls the embedding model to update embedding field.

## Installation

```pip install -r requirements.txt```

## Running App

Copy sample.env to .env and modify with connection string to your Atlas instance

```python main.py```