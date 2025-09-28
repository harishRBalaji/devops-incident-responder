import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def embed_chunks(chunks, model="text-embedding-3-small"):
    embeddings = []
    for chunk in chunks:
        resp = client.embeddings.create(model=model, input=chunk)
        embeddings.append(resp.data[0].embedding)
    return embeddings
