try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="Private PDF AI Search API")

# Add CORS middleware to allow the frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for the DB and models
db = None
rag_chain = None

def get_vectorstore():
    global db, rag_chain
    if db is not None:
        return
        
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2", google_api_key=api_key)
        db_dir = "chroma_db"
        
        if not os.path.exists(db_dir):
            logger.error("Chroma DB directory not found. Please run ingest_pdfs.py first.")
            return

        db = Chroma(persist_directory=db_dir, embedding_function=embeddings)
        
        # Initialize Gemini LLM with Fallbacks for 429 Quota errors
        llm1 = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, max_retries=0, google_api_key=api_key)
        llm2 = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2, max_retries=0, google_api_key=api_key)
        llm3 = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.2, max_retries=0, google_api_key=api_key)
        llm = llm1.with_fallbacks([llm2, llm3])
        
        # Setup Retriever
        retriever = db.as_retriever(search_kwargs={"k": 5})
        
        # Setup Prompt
        system_prompt = (
            "You are an expert AI assistant for reading ancient spiritual PDFs. "
            "IMPORTANT: REGARDLESS of whether the user's question is in Hindi, English, or Marathi, "
            "you MUST ALWAYS provide your final answer EXCLUSIVELY in the Marathi (मराठी) language.\n"
            "Use the following pieces of retrieved context to answer the question. "
            "If the answer is not in the context, say 'मला या PDF मध्ये ही माहिती सापडली नाही' (I couldn't find this in the PDFs). "
            "Do not hallucinate or use outside knowledge. Answer clearly, use Markdown formatting, and cite the Book Name and Page Number from the context.\n\n"
            "{context}"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])
        
        # Create Chain
        question_answer_chain = create_stuff_documents_chain(llm, prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)
        logger.info("Database and RAG chain initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing DB: {e}")

@app.on_event("startup")
async def startup_event():
    get_vectorstore()

class SearchQuery(BaseModel):
    query: str

class SourceContext(BaseModel):
    text: str
    metadata: dict

class SearchResponse(BaseModel):
    answer: str
    context: list[SourceContext]

@app.post("/api/search", response_model=SearchResponse)
async def search_pdf(request: SearchQuery):
    if not os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY") == "your_api_key_here":
        raise HTTPException(status_code=500, detail="Gemini API Key is not configured.")
        
    if rag_chain is None:
        get_vectorstore()
        
    if rag_chain is None:
        raise HTTPException(status_code=500, detail="Database not found or could not be loaded. Please ensure ingest_pdfs.py was run.")

    try:
        logger.info(f"Searching for: {request.query}")
        response = rag_chain.invoke({"input": request.query})
        
        sources = []
        import re
        for doc in response.get("context", []):
            text = doc.page_content
            # Extract page number
            page_match = re.search(r"## Page (\d+)", text)
            page_num = page_match.group(1) if page_match else "Unknown"
            
            # Extract book name
            book_name = doc.metadata.get("source", "Unknown Book")
            book_name = os.path.basename(book_name).replace(".md", "")
            
            # Clean text for transcript
            clean_text = re.sub(r"## Page \d+\s*", "", text).strip()
            
            # Add to metadata
            doc.metadata["page_number"] = page_num
            doc.metadata["book_name"] = book_name
            
            sources.append(SourceContext(
                text=clean_text,
                metadata=doc.metadata
            ))
            
        return SearchResponse(
            answer=response["answer"],
            context=sources
        )
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "db_loaded": db is not None}
