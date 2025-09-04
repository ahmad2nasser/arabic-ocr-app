# ### ARABIC PDF OCR WEB APP ###

import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import os
import io
import json
from google.oauth2 import service_account
from google.cloud import vision
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- Webpage Configuration ---
st.set_page_config(
    page_title="Arabic PDF OCR Tool",
    page_icon="📄",
    layout="wide"
)

# --- Helper Functions (Our original logic, adapted for the web app) ---

def convert_pdf_to_images(pdf_bytes):
    """Opens a PDF from memory and converts each page into an image."""
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    image_list = []
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Save image to a temporary in-memory file
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        image_list.append(img_byte_arr.getvalue())
        
    pdf_document.close()
    return image_list

def detect_text_in_image(image_bytes, client):
    """Sends a single image to Google Vision AI and gets the Arabic text."""
    image = vision.Image(content=image_bytes)
    response = client.text_detection(
        image=image,
        image_context={"language_hints": ["ar"]}
    )
    if response.text_annotations:
        return response.text_annotations[0].description
    else:
        return ""

# --- The Web App Interface ---

st.title("📄 Arabic PDF OCR Tool")
st.markdown("This tool extracts Arabic text from a PDF file using Google's Vision AI.")

# --- Sidebar for API Key Input ---
st.sidebar.header("Google API Credentials")
st.sidebar.markdown("""
    **Important:** You need a Google Cloud API Key to use this tool. 
    1.  Go to your Google Cloud project.
    2.  Find your Service Account.
    3.  Create a new key and download the JSON file.
    4.  Open the JSON file and copy its entire content.
    5.  Paste the content into the text box below.
""")

# Use a text area to accept the full JSON key content
api_key_json_str = st.sidebar.text_area("Paste your full Google Service Account JSON key here", height=250)

st.sidebar.markdown("---")
st.sidebar.info("Your API key is not stored. It is only used for this session.")

# --- Main Page for File Upload ---
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    # Add a button to start the process
    if st.button("🔍 Start OCR Process"):
        if not api_key_json_str:
            st.error("⚠️ Please paste your Google API Key in the sidebar to continue.")
        else:
            try:
                # Validate the JSON and create credentials
                credentials_info = json.loads(api_key_json_str)
                credentials = service_account.Credentials.from_service_account_info(credentials_info)
                client = vision.ImageAnnotatorClient(credentials=credentials)
                
                with st.spinner('Processing your PDF... This may take a few moments.'):
                    # Read the uploaded file from memory
                    pdf_bytes = uploaded_file.getvalue()
                    
                    # Step 1: Convert PDF to images
                    st.info("Step 1/3: Converting PDF pages to images...")
                    image_list = convert_pdf_to_images(pdf_bytes)
                    
                    # Step 2: Perform OCR on each image
                    st.info(f"Step 2/3: Sending {len(image_list)} pages to Google for OCR...")
                    full_text = []
                    progress_bar = st.progress(0)
                    for i, image_bytes in enumerate(image_list):
                        text_from_page = detect_text_in_image(image_bytes, client)
                        full_text.append(text_from_page)
                        progress_bar.progress((i + 1) / len(image_list))
                    
                    # Step 3: Prepare files for download
                    st.info("Step 3/3: Preparing your files for download...")
                    
                    base_filename = os.path.splitext(uploaded_file.name)[0]
                    
                    # Prepare TXT file
                    txt_output = '\u202B' + "\n\n--- Page Break ---\n\n".join(full_text)
                    
                    # Prepare DOCX file
                    doc = docx.Document()
                    for i, page_text in enumerate(full_text):
                        paragraph = doc.add_paragraph(page_text)
                        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                        if i < len(full_text) - 1:
                            doc.add_page_break()
                    
                    # Save docx to a temporary in-memory file
                    doc_byte_arr = io.BytesIO()
                    doc.save(doc_byte_arr)

                st.success("✅ Success! Your files are ready for download.")
                
                # --- Download Buttons ---
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="📥 Download as TXT",
                        data=txt_output.encode('utf-8'),
                        file_name=f"{base_filename}_OCR.txt",
                        mime="text/plain"
                    )
                with col2:
                    st.download_button(
                        label="📥 Download as DOCX",
                        data=doc_byte_arr.getvalue(),
                        file_name=f"{base_filename}_OCR.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

            except Exception as e:
                st.error(f"An error occurred: {e}")
                st.error("Please check your API key and make sure the Cloud Vision API is enabled for your project.")