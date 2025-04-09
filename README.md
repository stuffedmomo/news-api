# News API Project

A Python application that fetches news from the News API and processes it.

## Setup

1. Clone this repository
2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```
3. Install dependencies:
   ```
   pip install requests python-dotenv
   ```
4. Create a `.env` file in the root directory with your News API key:
   ```
   NEWS_API_KEY=your_api_key_here
   ```
   
   You can get an API key by signing up at [newsapi.org](https://newsapi.org)

5. Run the script:
   ```
   python news_RunDaily_USES_tokens.py
   ```

## Security Note

Never commit your `.env` file to version control. It's already added to `.gitignore` to prevent accidental commits. 