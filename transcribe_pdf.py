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

PDF_PATH = "pdfs/1976 - Dipavali.pdf"
MD_PATH = "pdfs/1976 - Dipavali.md"

def transcribe():
    global model, model_idx
    doc = fitz.open(PDF_PATH)
    total_pages = len(doc)
    
    start_page = 0
    if os.path.exists(MD_PATH):
        with open(MD_PATH, "r", encoding="utf-8") as f:
            content = f.read()
            import re
            matches = re.findall(r"## Page (\d+)", content)
            if matches:
                start_page = int(matches[-1])
                
    print(f"Opening {PDF_PATH}")
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

if __name__ == "__main__":
    transcribe()
