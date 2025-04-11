#!/usr/bin/env python3
import os
import json
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("feedback.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("feedback_system")

# Feedback categories
CATEGORIES = [
    'polity',
    'economy', 
    'international', 
    'environment', 
    'science', 
    'governance'
]

class FeedbackSystem:
    """
    Handles article feedback and ratings to improve content selection.
    
    This system allows users to rate articles with thumbs up/down,
    and uses this feedback to rank sources and keywords for better
    content filtering in the future.
    """
    
    def __init__(self, data_dir='feedback_data'):
        """Initialize the feedback system with a data directory."""
        self.data_dir = data_dir
        self.feedback_file = os.path.join(data_dir, 'article_feedback.json')
        self.source_ratings_file = os.path.join(data_dir, 'source_ratings.json')
        self.keyword_ratings_file = os.path.join(data_dir, 'keyword_ratings.json')
        
        # Ensure the data directory exists
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # Load existing data
        self.feedback_data = self._load_json(self.feedback_file, {})
        self.source_ratings = self._load_json(self.source_ratings_file, {})
        self.keyword_ratings = self._load_json(self.keyword_ratings_file, {})
    
    def _load_json(self, file_path, default_value):
        """Load JSON data from a file, returning a default value if the file doesn't exist."""
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Error loading {file_path}: {e}")
                # If the file is corrupted, create a backup
                backup_path = f"{file_path}.bak.{int(time.time())}"
                try:
                    os.rename(file_path, backup_path)
                    logger.info(f"Created backup of corrupted file: {backup_path}")
                except OSError as e:
                    logger.error(f"Failed to create backup: {e}")
        return default_value
    
    def _save_json(self, file_path, data):
        """Save JSON data to a file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving to {file_path}: {e}")
            return False
    
    def record_feedback(self, article_url, feedback, user_id=None, category=None):
        """
        Record user feedback for an article.
        
        Args:
            article_url (str): The URL of the article
            feedback (str): Either 'up' or 'down'
            user_id (str, optional): An identifier for the user, if available
            category (str, optional): Article category (polity, economy, etc.)
            
        Returns:
            bool: True if the feedback was successfully recorded
        """
        if feedback not in ('up', 'down'):
            logger.error(f"Invalid feedback value: {feedback}")
            return False
        
        # Normalize category
        if category and category.lower() in CATEGORIES:
            category = category.lower()
        elif category:
            logger.warning(f"Unknown category: {category}")
        
        # Create feedback entry
        timestamp = datetime.now().isoformat()
        
        feedback_entry = {
            'timestamp': timestamp,
            'feedback': feedback
        }
        
        if user_id:
            feedback_entry['user_id'] = user_id
            
        if category:
            feedback_entry['category'] = category
        
        # Add to feedback data
        if article_url not in self.feedback_data:
            self.feedback_data[article_url] = []
        
        self.feedback_data[article_url].append(feedback_entry)
        
        # Update source ratings if article has source info
        if article_url in self.feedback_data:
            # In a real system, we would look up the article's source
            # For now, just a placeholder
            source = self._extract_source_from_url(article_url)
            if source:
                self._update_source_rating(source, feedback, category)
        
        # Update keyword ratings based on article content
        # In a real system, we would analyze the article content
        # For now, just extract keywords from the URL
        keywords = self._extract_keywords_from_url(article_url)
        for keyword in keywords:
            self._update_keyword_rating(keyword, feedback, category)
        
        # Save the updated data
        success = self._save_json(self.feedback_file, self.feedback_data)
        self._save_json(self.source_ratings_file, self.source_ratings)
        self._save_json(self.keyword_ratings_file, self.keyword_ratings)
        
        return success
    
    def get_article_feedback(self, article_url):
        """Get all feedback for a specific article."""
        return self.feedback_data.get(article_url, [])
    
    def get_source_ratings(self, category=None):
        """
        Get source ratings, optionally filtered by category.
        
        Returns a dictionary of sources with their rating scores.
        """
        if category:
            # Filter by category
            filtered_ratings = {}
            for source, data in self.source_ratings.items():
                if category in data.get('categories', {}):
                    filtered_ratings[source] = {
                        'score': data.get('score', 0),
                        'upvotes': data.get('categories', {}).get(category, {}).get('upvotes', 0),
                        'downvotes': data.get('categories', {}).get(category, {}).get('downvotes', 0)
                    }
            return filtered_ratings
        else:
            # Return all sources with their overall scores
            return {source: data.get('score', 0) for source, data in self.source_ratings.items()}
    
    def get_keyword_ratings(self, category=None):
        """
        Get keyword ratings, optionally filtered by category.
        
        Returns a dictionary of keywords with their rating scores.
        """
        if category:
            # Filter by category
            filtered_ratings = {}
            for keyword, data in self.keyword_ratings.items():
                if category in data.get('categories', {}):
                    filtered_ratings[keyword] = {
                        'score': data.get('score', 0),
                        'upvotes': data.get('categories', {}).get(category, {}).get('upvotes', 0),
                        'downvotes': data.get('categories', {}).get(category, {}).get('downvotes', 0)
                    }
            return filtered_ratings
        else:
            # Return all keywords with their overall scores
            return {keyword: data.get('score', 0) for keyword, data in self.keyword_ratings.items()}
    
    def get_top_sources(self, category=None, limit=10):
        """Get the top-rated sources, optionally filtered by category."""
        ratings = self.get_source_ratings(category)
        sorted_sources = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
        return sorted_sources[:limit]
    
    def get_top_keywords(self, category=None, limit=20):
        """Get the top-rated keywords, optionally filtered by category."""
        ratings = self.get_keyword_ratings(category)
        sorted_keywords = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
        return sorted_keywords[:limit]
    
    def _update_source_rating(self, source, feedback, category=None):
        """Update the rating for a source based on feedback."""
        if source not in self.source_ratings:
            self.source_ratings[source] = {
                'score': 0,
                'upvotes': 0,
                'downvotes': 0,
                'categories': {}
            }
        
        # Update overall counts
        if feedback == 'up':
            self.source_ratings[source]['upvotes'] = self.source_ratings[source].get('upvotes', 0) + 1
        else:
            self.source_ratings[source]['downvotes'] = self.source_ratings[source].get('downvotes', 0) + 1
        
        # Calculate new score
        upvotes = self.source_ratings[source].get('upvotes', 0)
        downvotes = self.source_ratings[source].get('downvotes', 0)
        total = upvotes + downvotes
        
        if total > 0:
            # Simple score formula: (upvotes - downvotes) / total
            score = (upvotes - downvotes) / total
            self.source_ratings[source]['score'] = score
        
        # Update category-specific ratings if a category is provided
        if category:
            if category not in self.source_ratings[source]['categories']:
                self.source_ratings[source]['categories'][category] = {
                    'upvotes': 0,
                    'downvotes': 0,
                    'score': 0
                }
            
            if feedback == 'up':
                self.source_ratings[source]['categories'][category]['upvotes'] += 1
            else:
                self.source_ratings[source]['categories'][category]['downvotes'] += 1
            
            # Calculate category-specific score
            cat_upvotes = self.source_ratings[source]['categories'][category].get('upvotes', 0)
            cat_downvotes = self.source_ratings[source]['categories'][category].get('downvotes', 0)
            cat_total = cat_upvotes + cat_downvotes
            
            if cat_total > 0:
                cat_score = (cat_upvotes - cat_downvotes) / cat_total
                self.source_ratings[source]['categories'][category]['score'] = cat_score
    
    def _update_keyword_rating(self, keyword, feedback, category=None):
        """Update the rating for a keyword based on feedback."""
        if keyword not in self.keyword_ratings:
            self.keyword_ratings[keyword] = {
                'score': 0,
                'upvotes': 0,
                'downvotes': 0,
                'categories': {}
            }
        
        # Update overall counts
        if feedback == 'up':
            self.keyword_ratings[keyword]['upvotes'] = self.keyword_ratings[keyword].get('upvotes', 0) + 1
        else:
            self.keyword_ratings[keyword]['downvotes'] = self.keyword_ratings[keyword].get('downvotes', 0) + 1
        
        # Calculate new score
        upvotes = self.keyword_ratings[keyword].get('upvotes', 0)
        downvotes = self.keyword_ratings[keyword].get('downvotes', 0)
        total = upvotes + downvotes
        
        if total > 0:
            # Simple score formula: (upvotes - downvotes) / total
            score = (upvotes - downvotes) / total
            self.keyword_ratings[keyword]['score'] = score
        
        # Update category-specific ratings if a category is provided
        if category:
            if category not in self.keyword_ratings[keyword]['categories']:
                self.keyword_ratings[keyword]['categories'][category] = {
                    'upvotes': 0,
                    'downvotes': 0,
                    'score': 0
                }
            
            if feedback == 'up':
                self.keyword_ratings[keyword]['categories'][category]['upvotes'] += 1
            else:
                self.keyword_ratings[keyword]['categories'][category]['downvotes'] += 1
            
            # Calculate category-specific score
            cat_upvotes = self.keyword_ratings[keyword]['categories'][category].get('upvotes', 0)
            cat_downvotes = self.keyword_ratings[keyword]['categories'][category].get('downvotes', 0)
            cat_total = cat_upvotes + cat_downvotes
            
            if cat_total > 0:
                cat_score = (cat_upvotes - cat_downvotes) / cat_total
                self.keyword_ratings[keyword]['categories'][category]['score'] = cat_score
    
    def _extract_source_from_url(self, url):
        """Extract the source name from a URL."""
        try:
            import re
            from urllib.parse import urlparse
            
            # Parse the URL
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Remove www. if present
            domain = re.sub(r'^www\.', '', domain)
            
            # Extract the main domain (e.g., thehindu.com from www.thehindu.com)
            parts = domain.split('.')
            if len(parts) >= 2:
                return parts[-2]
            return domain
        except Exception as e:
            logger.error(f"Error extracting source from URL {url}: {e}")
            return None
    
    def _extract_keywords_from_url(self, url):
        """Extract potential keywords from a URL."""
        try:
            import re
            from urllib.parse import urlparse, unquote
            
            # Parse the URL
            parsed_url = urlparse(url)
            path = unquote(parsed_url.path)
            
            # Split the path into parts
            path_parts = path.split('/')
            path_parts = [p for p in path_parts if p]
            
            # Extract words from the path parts
            keywords = []
            for part in path_parts:
                # Replace non-alphanumeric chars with spaces
                words = re.sub(r'[^a-zA-Z0-9]', ' ', part).split()
                keywords.extend([w.lower() for w in words if len(w) > 3])
            
            return keywords
        except Exception as e:
            logger.error(f"Error extracting keywords from URL {url}: {e}")
            return []

# API endpoint handler for the web server
def handle_feedback_request(post_data):
    """
    Handle a feedback request from the web server.
    
    Args:
        post_data (dict): The POST data from the request
        
    Returns:
        dict: Response data
    """
    try:
        article_url = post_data.get('url')
        feedback = post_data.get('feedback')
        category = post_data.get('category')
        user_id = post_data.get('user_id')
        
        if not article_url or not feedback:
            return {
                'success': False,
                'error': 'Missing required fields: url and feedback'
            }
        
        # Initialize feedback system
        feedback_system = FeedbackSystem()
        
        # Record the feedback
        success = feedback_system.record_feedback(
            article_url=article_url,
            feedback=feedback,
            user_id=user_id,
            category=category
        )
        
        if success:
            return {
                'success': True,
                'message': 'Feedback recorded successfully'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to record feedback'
            }
    except Exception as e:
        logger.error(f"Error handling feedback request: {e}")
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    # Test the feedback system
    feedback_system = FeedbackSystem()
    
    # Record some test feedback
    test_urls = [
        'https://www.thehindu.com/news/national/article1234.ece',
        'https://www.thehindu.com/business/economy-growth-report/article5678.ece',
        'https://pib.gov.in/PressReleasePage.aspx?PRID=1234567',
        'https://timesofindia.indiatimes.com/india/article987654.cms'
    ]
    
    for url in test_urls:
        # Record random feedback
        import random
        feedback = 'up' if random.random() > 0.5 else 'down'
        category = random.choice(CATEGORIES)
        
        print(f"Recording {feedback} for {url} in category {category}")
        feedback_system.record_feedback(url, feedback, category=category)
    
    # Print top sources
    print("\nTop sources:")
    for source, score in feedback_system.get_top_sources():
        print(f"  {source}: {score:.2f}")
    
    # Print top keywords
    print("\nTop keywords:")
    for keyword, score in feedback_system.get_top_keywords():
        print(f"  {keyword}: {score:.2f}")
    
    # Print top sources for a specific category
    category = 'economy'
    print(f"\nTop sources for {category}:")
    for source, score in feedback_system.get_top_sources(category):
        print(f"  {source}: {score:.2f}") 