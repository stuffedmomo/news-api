# News Portal

A comprehensive news aggregation and curation system designed specifically for UPSC (Union Public Service Commission) examination preparation. The application fetches, processes, and categorizes news from various sources, making it easier for UPSC aspirants to stay updated with relevant current affairs.

## Features

- **Automatic News Aggregation**: Daily fetching of news from NewsAPI and various RSS feeds
- **Topic Categorization**: News articles are automatically categorized into UPSC-relevant topics
- **Clean Web Interface**: Newspaper-style reading experience with mobile-friendly design
- **Feedback System**: Thumbs up/down mechanism to improve content relevance over time
- **Offline Reading**: News stored in markdown format for easy offline access
- **Content Caching**: Efficient caching system to reduce API calls and improve performance

## Project Structure

```
news-api/
│
├── setup.py                    # Setup script for installing dependencies
├── upsc_news_daily.py          # Main script for fetching daily news
├── upsc_web_server.py          # Web server for UI
├── news_api_utils.py           # Utilities for NewsAPI integration
├── rss_crawler.py              # RSS feed fetching and content extraction
├── feedback_system.py          # Thumbs up/down user feedback system
│
├── news_data/                  # Stored news article markdown files
│   ├── sources.md              # News sources information
│   ├── global_headlines.md     # Global headlines
│   ├── business_headlines.md   # Business news
│   ├── india_news.md           # India-specific news
│   ├── upsc_economy.md         # Economy news for UPSC
│   ├── upsc_environment.md     # Environment news for UPSC
│   ├── upsc_international.md   # International relations news for UPSC
│   ├── upsc_governance.md      # Governance news for UPSC
│   ├── upsc_polity.md          # Polity news for UPSC
│   └── upsc_science.md         # Science & tech news for UPSC
│
├── web/                        # Web interface files
│   ├── index.html              # Main HTML file (newspaper style)
│   ├── css/
│   │   └── newspaper-style.css # Newspaper-style CSS
│   └── js/
│       └── news-portal.js      # Frontend JavaScript for the portal
```

## Setup

1. Clone this repository
2. Run the setup script to create necessary directories and install dependencies:
   ```
   python setup.py --full-setup
   ```
3. Enter your NewsAPI key when prompted (or create a `.env` file with `NEWS_API_KEY=your_key_here`)
4. Start the web server:
   ```
   python upsc_web_server.py
   ```
5. To fetch fresh news content:
   ```
   python upsc_news_daily.py
   ```

## Usage

1. Open your browser and navigate to `http://localhost:5000` (or the configured port)
2. Browse news by category using the sidebar navigation
3. Use the search functionality to find specific topics
4. Provide feedback on articles to improve future content

## Security Note

Never commit your `.env` file to version control. It's already added to `.gitignore` to prevent accidental commits. 
