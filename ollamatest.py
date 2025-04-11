import sys
import subprocess
import importlib.util

# Function to check and install required packages
def ensure_package(package):
    if importlib.util.find_spec(package.split('-')[0].replace('_', '')) is None:
        print(f"Installing required package: {package}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"Successfully installed {package}")

# Install required packages
required_packages = ["langchain-ollama", "langchain-community", "langchain-text-splitters"]
for package in required_packages:
    ensure_package(package)

# Now import after ensuring packages are installed
from langchain_ollama.llms import OllamaLLM
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import re

# Initialize the LLM
llm = OllamaLLM(model="llama3.2:1b", streaming=True)

# Load the specific markdown file
 

# Load the markdown content
loader = TextLoader(file_path)
markdown_document = loader.load()[0]
markdown_text = markdown_document.page_content

# Print some debug info
print(f"Loaded markdown file with {len(markdown_text)} characters")

# Function to split text into article sections using regex
def split_into_articles(text):
    # Split by the "## " headers which indicate individual articles
    pattern = r"## \d+\. (.+?)(?=\n## \d+\.|$)"
    articles = re.findall(pattern, text, re.DOTALL)
    
    # Extract titles separately to use as metadata
    title_pattern = r"## \d+\. (.+?)(?=\n)"
    titles = re.findall(title_pattern, text)
    
    # Create document chunks with title metadata
    article_chunks = []
    for i, (title, content) in enumerate(zip(titles, articles)):
        full_section = f"## {i+1}. {title}\n{content}"
        article_chunks.append({"title": title, "content": full_section})
    
    return article_chunks

# Split the markdown text into articles
article_chunks = split_into_articles(markdown_text)

# Process each article separately
print(f"Found {len(article_chunks)} articles. Processing each for insights...\n")

for i, article in enumerate(article_chunks):
    # Extract article title
    title = article["title"]
    content = article["content"]
    
    # Print separator for better readability
    print(f"\n{'='*80}\n{i+1}. ANALYZING: {title}\n{'='*80}\n")
    
    # Create prompt for insights
    prompt = f"Provide 3-5 key business insights from this news article. Focus on market implications, economic trends, and strategic business considerations:\n\n{content}"
    
    # Stream the response
    response_stream = llm.stream(prompt)
    
    sys.stdout.write("INSIGHTS:\n")
    for chunk in response_stream:
        sys.stdout.write(chunk)
        sys.stdout.flush()
    
    # Add separator after each article
    if i < len(article_chunks) - 1:
        print("\n")

print("\nAnalysis complete for all articles.")