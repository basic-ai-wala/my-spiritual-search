import os
import streamlit as st
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

st.set_page_config(page_title="Private PDF Search", page_icon="📄")

# Check for API Key
if "GEMINI_API_KEY" not in os.environ or not os.environ["GEMINI_API_KEY"] or os.environ["GEMINI_API_KEY"] == "your_api_key_here":
    st.error("Please add your Google Gemini API Key in the `.env` file to continue.")
    st.stop()

@st.cache_resource
def get_vectorstore():
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
    db_dir = "chroma_db"
    if not os.path.exists(db_dir):
        return None
    db = Chroma(persist_directory=db_dir, embedding_function=embeddings)
    return db

db = get_vectorstore()

st.title("📄 Private PDF AI Search")
st.markdown("Search through your pre-loaded PDFs. AI will only answer based on those documents.")

if db is None:
    st.warning("Database not found. Please run `py ingest_pdfs.py` first after placing PDFs in the `pdfs` folder.")
    st.stop()

query = st.text_input("अपना सवाल यहाँ पूछें (Ask your question here):")

if query:
    with st.spinner("Searching and summarizing... (जानकारी ढूंढी जा रही है...)"):
        try:
            # Initialize Gemini LLM
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2)
            
            # Setup Retriever
            retriever = db.as_retriever(search_kwargs={"k": 5})
            
            # Setup Prompt
            system_prompt = (
                "You are an assistant for question-answering tasks. "
                "Use the following pieces of retrieved context to answer the question. "
                "If the answer is not in the context, say 'मुझे यह जानकारी PDF में नहीं मिली (I couldn't find this in the PDFs)'. "
                "Do not hallucinate or use outside knowledge. Answer clearly and summarize if needed.\n\n"
                "{context}"
            )
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}"),
            ])
            
            # Create Chain
            question_answer_chain = create_stuff_documents_chain(llm, prompt)
            rag_chain = create_retrieval_chain(retriever, question_answer_chain)
            
            # Execute Query
            response = rag_chain.invoke({"input": query})
            
            st.markdown("### जवाब (Answer):")
            st.write(response["answer"])
            
            # Optionally show sources
            with st.expander("Reference context used"):
                for doc in response["context"]:
                    st.write(doc.page_content)
                    st.write("---")
        except Exception as e:
            st.error(f"Error generating answer: {e}")
