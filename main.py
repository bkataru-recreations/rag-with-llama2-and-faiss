import os
import re
import markdown
from pdfminer.high_level import extract_text as extract_text_from_pdf
from io import StringIO
from html.parser import HTMLParser
from langchain.text_splitter import RecursiveCharacterTextSplitter

# HTML Stripper class to clean HTML tags from the text
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)
    
    def get_data(self):
        return self.text.getvalue()

def strip_tags(html):
    """Remove HTML tags from a string."""
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def clean_markdown(text):
    """Clean Markdown syntax from text."""

    # Remove Markdown URL links
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove bold and italic text markers
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)

    # Remove images and their references
    text = re.sub(r'!\[[^\]]]*]\([^)]*\)', '', text)

    # Remove header markers
    text = re.sub(r'#+\s?', '', text)

    # Remove other Markdown syntax as needed (e.g., tables, bullet points)
    text = re.sub(r'\|', ' ', text)
    text = re.sub(r'-{2,}', '', text)
    text = re.sub(r'\n{2,}', '\n', text)  # Remove extra newlines

    return text

def extract_text_from_md(md_path):
    """Extract and clean text from a Markdown file."""

    with open(md_path, "r", encoding="utf-8") as file:
        md_content = file.read()
        html = markdown.markdown(md_content)
        text = strip_tags(html)

        return clean_markdown(text)

def extract_text_from_file(file_path):
    """Extract text from a file based on its extension."""

    if file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith('.md'):
        return extract_text_from_md(file_path)
    elif file_path.endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    else:
        return "Unsupported file format."

# Directory containing documents to process
directory = r'./corpus/'

# Parameters for text splitting
chunk_size = 1200
chunk_overlap = 300

# List to store all document chunks
all_docs = []
allowed_extensions = ['.md', '.pdf', '.txt']

# Process each file in the directory
for root, dirs, files in os.walk(directory):
    for filename in files:
        # Get the file extension
        _, file_extension = os.path.splitext(filename)
        if file_extension in allowed_extensions:
            file_path = os.path.join(root, filename) # Full path of the file

            # Remove the ".md", ".pdf", or ".txt" extension from the file name
            file_name_without_extension = os.path.splitext(filename)[0]

            # Open and read the file
            file_content = extract_text_from_file(file_path)

            # Split the text into chunks
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            docs = text_splitter.split_text(file_content)

            for i, chunk in enumerate(docs):
                # Define metadata for each chunk (can customize this)

                metadata = {
                    "File Name": file_name_without_extension,
                    "Chunk Number": i + 1,
                }

                # Create a header with metadata and file name
                header = f"File Name: {file_name_without_extension}\n"
                for key, value in metadata.items():
                    header += f"{key}: {value}\n"

                # Combine header, file name, and chunk content
                chunk_with_header = header + file_name_without_extension + "\n" + chunk

                all_docs.append(chunk_with_header)

            print(f"Processed: {filename}")

from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceInstructEmbeddings

# Initialize HuggingFaceInstructEmbeddings
model_name = "hkunlp/instructor-large"
model_kwargs = {'device': 'cpu'}
encode_kwargs = {'normalize_embeddings': True}
hf_embedding = HuggingFaceInstructEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs
)

# Embed and index all the documents using FAISS
db = FAISS.from_texts(all_docs, hf_embedding)

# Save the indexed data locally
db.save_local("faiss_AiDoc")

# Load the FAISS index from local storage
db = FAISS.load_local("faiss_AiDoc", embeddings=hf_embedding)