import os
from dotenv import load_dotenv
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

# Load environment variables
load_dotenv()

# Ensure API key is set
if "GEMINI_API_KEY" not in os.environ or not os.environ["GEMINI_API_KEY"] or os.environ["GEMINI_API_KEY"] == "your_api_key_here":
    print("Error: Please set GEMINI_API_KEY in your .env file.")
    exit(1)

def ingest_data():
    pdf_dir = "pdfs"
    db_dir = "chroma_db"
    
    if not os.path.exists(pdf_dir):
        print(f"Error: Directory '{pdf_dir}' not found. Please create it and add PDFs.")
        exit(1)

    print("Loading Markdown documents...")
    loader = DirectoryLoader(pdf_dir, glob="**/*.md", loader_cls=UnstructuredMarkdownLoader)
    documents = loader.load()
    
    if not documents:
        print(f"No Markdown documents found in '{pdf_dir}'. Please add some PDFs/MDs and try again.")
        exit(1)
        
    print(f"Loaded {len(documents)} document pages.")

    print("Splitting text into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks.")

    print("Generating embeddings and saving to ChromaDB...")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
    
    # Create and persist vector database in batches to avoid API limits
    import time
    batch_size = 20
    db = None
    
    # We may have already processed batch 1 in the previous run, but it's safer to re-create
    # the whole DB since we deleted chroma_db.
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1} ({len(batch)} chunks)...")
        
        # Add internal retry loop for the batch
        success = False
        retries = 3
        while not success and retries > 0:
            try:
                if db is None:
                    db = Chroma.from_documents(
                        documents=batch,
                        embedding=embeddings,
                        persist_directory=db_dir
                    )
                else:
                    db.add_documents(batch)
                success = True
            except Exception as e:
                print(f"Error on batch {i//batch_size + 1}, retrying... {e}")
                time.sleep(30)
                retries -= 1
                
        print(f"Batch {i//batch_size + 1} added to Chroma.")
        time.sleep(15) # Wait 15s to respect the 100 requests per minute limit
        
    if hasattr(db, 'persist'):
        db.persist()
        
    print(f"Success! Data saved to '{db_dir}'.")

if __name__ == "__main__":
    ingest_data()
