import chromadb
from chromadb.utils import embedding_functions

# Initialize Chroma client (persistent)
client = chromadb.PersistentClient(path="./chroma_db")
embedding_fn = embedding_functions.DefaultEmbeddingFunction()

def query_jobs(company_name=None, query_text=None, n_results=10, count_only=False):
    """
    Query jobs semantically or filter by company/keyword.
    If count_only=True → returns number of matched jobs.
    """
    collections = client.list_collections()
    if not collections:
        print("⚠️ No collections found in ChromaDB.")
        return []

    matched_docs = []
    for col_info in collections:
        collection = client.get_collection(col_info.name, embedding_function=embedding_fn)

        # If company filter is given, skip others
        if company_name and company_name.lower() not in col_info.name.lower():
            continue

        # If query text is provided → semantic search
        if query_text:
            results = collection.query(query_texts=[query_text], n_results=n_results)
            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                matched_docs.append({
                    "company": meta.get("company", col_info.name),
                    "title": meta.get("title", ""),
                    "location": meta.get("location", ""),
                    "url": meta.get("url", ""),
                    "preview": doc[:150] + "..."
                })
        else:
            # Return all jobs if no query
            all_docs = collection.get()
            for doc, meta in zip(all_docs["documents"], all_docs["metadatas"]):
                matched_docs.append({
                    "company": meta.get("company", col_info.name),
                    "title": meta.get("title", ""),
                    "location": meta.get("location", ""),
                    "url": meta.get("url", ""),
                    "preview": doc[:150] + "..."
                })

    if count_only:
        return len(matched_docs)
    return matched_docs
