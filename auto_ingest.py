import os
import time
import re
import fitz
from dotenv import load_dotenv
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()

PDF_PATHS = [
    ("pdfs/1979 - Dipavali.pdf", "pdfs/1979 - Dipavali.md"),
    ("pdfs/1980 - April-May-Jun.pdf", "pdfs/1980 - April-May-Jun.md"),
    ("pdfs/1980 - Dipavali.pdf", "pdfs/1980 - Dipavali.md"),
    ("pdfs/1980 - July-Aug-Sep.pdf", "pdfs/1980 - July-Aug-Sep.md"),
    ("pdfs/1981 - Jan-Feb-March.pdf", "pdfs/1981 - Jan-Feb-March.md"),
    ("pdfs/1981 - July-Aug-Sep.pdf", "pdfs/1981 - July-Aug-Sep.md"),
    ("pdfs/1981 - Oct-Nov-Des.pdf", "pdfs/1981 - Oct-Nov-Des.md"),
    ("pdfs/1982 - Devendranath Visheshank.pdf", "pdfs/1982 - Devendranath Visheshank.md"),
    ("pdfs/1982 - Jan-Feb-March.pdf", "pdfs/1982 - Jan-Feb-March.md"),
    ("pdfs/1983 - Dipavali.pdf", "pdfs/1983 - Dipavali.md"),
    ("pdfs/1984 - Dipavali.pdf", "pdfs/1984 - Dipavali.md"),
]

def check_if_done(pdf_path, md_path):
    if not os.path.exists(md_path): return False
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
            matches = re.findall(r"## Page (\d+)", content)
            if matches:
                last_page = int(matches[-1])
                return last_page >= total_pages
    except:
        pass
    return False

def ingest_file(md_path):
    db_dir = "chroma_db"
    print(f"Loading {md_path}...")
    loader = UnstructuredMarkdownLoader(md_path)
    documents = loader.load()
    if not documents: return
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
    db = Chroma(persist_directory=db_dir, embedding_function=embeddings)
    
    batch_size = 20
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        success = False
        retries = 3
        while not success and retries > 0:
            try:
                db.add_documents(batch)
                success = True
            except Exception as e:
                time.sleep(30)
                retries -= 1
        time.sleep(15)
    print(f"Ingested {md_path} successfully!")

def watch_and_ingest():
    ingested = set()
    while len(ingested) < len(PDF_PATHS):
        for pdf_path, md_path in PDF_PATHS:
            if md_path not in ingested:
                if check_if_done(pdf_path, md_path):
                    print(f"Found completed transcription: {md_path}")
                    ingest_file(md_path)
                    ingested.add(md_path)
        print("Sleeping 60 seconds before checking again...")
        time.sleep(60)
    print("All files auto-ingested!")

if __name__ == "__main__":
    watch_and_ingest()
