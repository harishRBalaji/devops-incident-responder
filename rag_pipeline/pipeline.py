from loader import load_pdf
from chunker import chunk_text
from embedder import embed_chunks
from pinecone_store import PineconeStore

def build_rag_index(pdf_path: str):
    text = load_pdf(pdf_path)
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    embeddings = embed_chunks(chunks)

    store = PineconeStore()
    store.upsert(embeddings, chunks)

if __name__ == "__main__":
    build_rag_index("RAG Document.pdf")
