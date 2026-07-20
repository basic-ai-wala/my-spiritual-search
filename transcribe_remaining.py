import os
import io
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
import time
import re

load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-2.5-pro",
    "gemini-3-pro-preview",
    "gemini-3.1-pro-preview",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
]
model_idx = 0
model = genai.GenerativeModel(MODELS[model_idx])

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

def transcribe():
    global model, model_idx
    for PDF_PATH, MD_PATH in PDF_PATHS:
        print(f"\n======================================")
        print(f"Starting {PDF_PATH}")
        print(f"======================================\n")
        
        doc = fitz.open(PDF_PATH)
        total_pages = len(doc)
        
        start_page = 0
        if os.path.exists(MD_PATH):
            with open(MD_PATH, "r", encoding="utf-8") as f:
                content = f.read()
                matches = re.findall(r"## Page (\d+)", content)
                if matches:
                    start_page = int(matches[-1])
                    
        print(f"Resuming from page {start_page + 1}")
        
        page_num = start_page
        while page_num < total_pages:
            page = doc[page_num]
            print(f"Processing page {page_num + 1}/{total_pages} using {MODELS[model_idx]}...")
            
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
            img_bytes = pix.tobytes("jpeg")
            img = Image.open(io.BytesIO(img_bytes))
            
            prompt = (
                "You are an expert transcriber. Transcribe the Hindi text from this image exactly as it appears. "
                "Do not translate it, do not summarize it. Just output the text in Devanagari script."
            )
            
            try:
                response = model.generate_content([prompt, img])
                text = response.text
                
                with open(MD_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n\n## Page {page_num + 1}\n\n{text}\n")
                print(f"Successfully appended page {page_num + 1}.")
                
                time.sleep(2)
                page_num += 1
                
            except Exception as e:
                err_str = str(e)
                print(f"Error on page {page_num + 1}: {err_str}")
                if "429" in err_str or "Quota" in err_str:
                    model_idx += 1
                    if model_idx >= len(MODELS):
                        print("All models exhausted! Sleeping for 60 seconds to retry...")
                        model_idx = 0
                        time.sleep(60)
                    else:
                        print(f"Switching to next model: {MODELS[model_idx]}")
                        model = genai.GenerativeModel(MODELS[model_idx])
                else:
                    print("Unknown error. Sleeping for 10 seconds...")
                    time.sleep(10)
        
        print(f"Finished {PDF_PATH}!")

if __name__ == "__main__":
    transcribe()
