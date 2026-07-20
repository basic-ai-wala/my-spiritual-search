import os
from dotenv import load_dotenv
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()

def ingest_data():
    db_dir = "chroma_db"
    files_to_ingest = ["pdfs/1977 - Dipavali.md"]
    
    documents = []
    for f in files_to_ingest:
        if os.path.exists(f):
            print(f"Loading {f}...")
            loader = UnstructuredMarkdownLoader(f)
            documents.extend(loader.load())
        else:
            print(f"File {f} not found!")
            
    if not documents:
        print("No documents loaded.")
        return

    print("Splitting text into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks.")

    print("Generating embeddings and saving to ChromaDB...")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
    
    import time
    batch_size = 20
    db = Chroma(persist_directory=db_dir, embedding_function=embeddings)
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1} ({len(batch)} chunks)...")
        success = False
        retries = 3
        while not success and retries > 0:
            try:
                db.add_documents(batch)
                success = True
            except Exception as e:
                print(f"Error on batch {i//batch_size + 1}, retrying... {e}")
                time.sleep(30)
                retries -= 1
        print(f"Batch {i//batch_size + 1} added to Chroma.")
        time.sleep(15)
        
    print(f"Success! Data saved to '{db_dir}'.")

if __name__ == "__main__":
    ingest_data()
