import http.server
import socketserver
import os
import markdown
import json # Added for API endpoint
from urllib.parse import urlparse, unquote

# Directory where markdown files are stored
NEWS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "news_data")
# Directory for web files (relative to where the script is run)
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web") # Ensure WEB_DIR points to the correct subfolder

# Custom request handler class
class NewsServerHandler(http.server.SimpleHTTPRequestHandler):
    # Override directory setting for SimpleHTTPRequestHandler
    # This tells it where to serve files from by default
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # API Endpoint to list news files
        if path == '/api/files':
            try:
                files = [f for f in os.listdir(NEWS_DIR) if f.endswith('.md')]
                # Create a list of dictionaries with filename and title
                file_data = []
                for file in files:
                    title = file.replace('.md', '').replace('_', ' ').title()
                    file_data.append({'filename': file, 'title': title})
                    
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(file_data).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
            return
            
        # Serve the view endpoint for markdown conversion
        if path.startswith('/view/'):
            filename = unquote(path[len('/view/'):]) # Correct slicing
            filepath = os.path.join(NEWS_DIR, filename)
            
            if os.path.exists(filepath) and os.path.isfile(filepath):
                try:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8') # Specify UTF-8
                    self.end_headers()
                    
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Convert markdown to HTML
                        html_content = markdown.markdown(content)
                        self.wfile.write(html_content.encode('utf-8'))
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(f'Error processing file: {e}'.encode('utf-8'))
            else:
                self.send_error(404, 'File Not Found')
            return
        
        # For all other paths, let SimpleHTTPRequestHandler serve files from WEB_DIR
        # The directory is set in __init__, so super().do_GET() works correctly
        return super().do_GET()

# Run the server
PORT = 8000
# Ensure the server binds to all interfaces if needed, or just localhost
# ADDRESS = "0.0.0.0" # Bind to all interfaces
ADDRESS = "127.0.0.1" # Bind to localhost only

Handler = NewsServerHandler

with socketserver.TCPServer((ADDRESS, PORT), Handler) as httpd:
    print(f"Serving from directory: {WEB_DIR}")
    print(f"News data directory: {NEWS_DIR}")
    print(f"Server running at http://{ADDRESS}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.shutdown()