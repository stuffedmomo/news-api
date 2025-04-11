/**
 * UPSC News Portal JavaScript
 * Handles API interactions and UI updates
 */

// Global state for user preferences
const appState = {
    selectedCategory: 'all',
    feedbackData: {}, // Store article feedback
    lastSearchQuery: '',
    countryPreference: 'in',
    isLoading: false
};

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    console.log('Initializing UPSC News Portal...');
    
    // Initialize navigation
    setupNavigation();
    
    // Set up category navigation
    setupCategoryLinks();
    
    // Set up API buttons
    setupAPIButtons();
    
    // Load news files list
    loadNewsFilesList();
    
    // Load recent headlines for welcome page
    loadRecentHeadlines();
    
    // Set up feedback system
    setupFeedbackSystem();
    
    // Try to load saved preferences
    loadSavedPreferences();

     // Start the clock - add these two lines
     updateClock();
     setInterval(updateClock, 1000);
    
    // Update last updated timestamp
    document.getElementById('last-updated').textContent = new Date().toLocaleString();
}

// Set up main navigation
function setupNavigation() {
    // Home link
    document.getElementById('home-link').addEventListener('click', function(e) {
        e.preventDefault();
        showSection('welcome-section');
    });
    
    // Top Headlines link
    document.getElementById('top-headlines-link').addEventListener('click', function(e) {
        e.preventDefault();
        showSection('top-headlines-section');
        loadTopHeadlines(appState.countryPreference, document.getElementById('category').value);
    });
    
    // Everything link
    document.getElementById('everything-link').addEventListener('click', function(e) {
        e.preventDefault();
        showSection('everything-section');
    });
    
    // Sources link
    document.getElementById('sources-link').addEventListener('click', function(e) {
        e.preventDefault();
        showSection('sources-section');
        loadSources();
    });
    
    // Back buttons
    document.querySelectorAll('.back-button').forEach(button => {
        button.addEventListener('click', function() {
            // Determine if this is the back button in the file content section
            if (this.closest('#file-content-section')) {
                // Navigate back to the welcome section (home)
                showSection('welcome-section');
            } else {
                // Use browser history for other back buttons
                history.back();
            }
        });
    });
}

// Set up category links
function setupCategoryLinks() {
    const categoryLinks = document.querySelectorAll('#category-list a');
    categoryLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all links
            categoryLinks.forEach(l => l.parentElement.classList.remove('active'));
            
            // Add active class to clicked link
            this.parentElement.classList.add('active');
            
            // Store selected category
            appState.selectedCategory = this.getAttribute('data-category');
            savePreferences();
            
            // Load category news
            loadCategoryNews(appState.selectedCategory);
        });
    });
}

// Set up API buttons
function setupAPIButtons() {
    // Load Top Headlines button
    document.getElementById('load-headlines').addEventListener('click', function() {
        const country = document.getElementById('country').value;
        appState.countryPreference = country; // Save preference
        savePreferences();
        
        const category = document.getElementById('category').value;
        loadTopHeadlines(country, category);
    });
    
    // Search button
    document.getElementById('run-search').addEventListener('click', function() {
        const query = document.getElementById('search-query').value;
        if (!query) {
            alert('Please enter search keywords');
            return;
        }
        
        // Save last search
        appState.lastSearchQuery = query;
        savePreferences();
        
        const searchIn = document.getElementById('search-in').value;
        const language = document.getElementById('language').value;
        const fromDate = document.getElementById('from-date').value;
        const toDate = document.getElementById('to-date').value;
        const sortBy = document.getElementById('sort-by').value;
        
        runSearch(query, searchIn, language, fromDate, toDate, sortBy);
    });
    
    // Toggle advanced filters
    const advancedFiltersToggle = document.createElement('button');
    advancedFiltersToggle.textContent = 'Advanced Filters';
    advancedFiltersToggle.className = 'advanced-filters-toggle';
    advancedFiltersToggle.addEventListener('click', function() {
        const advancedFilters = document.getElementById('advanced-filters');
        advancedFilters.style.display = advancedFilters.style.display === 'none' ? 'block' : 'none';
        this.textContent = advancedFilters.style.display === 'none' ? 'Advanced Filters' : 'Hide Advanced Filters';
    });
    
    // Add the toggle button to the everything section filters
    const everythingFilters = document.querySelector('#everything-section .filters');
    everythingFilters.appendChild(advancedFiltersToggle);
}

// Helper function to show only one section
function showSection(sectionId) {
    const sections = [
        'welcome-section', 
        'top-headlines-section', 
        'everything-section', 
        'article-view', 
        'sources-section',
        'file-content-section'
    ];
    
    sections.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.style.display = id === sectionId ? 'block' : 'none';
        }
    });
}

// Function to load news files list
function loadNewsFilesList() {
    const listElement = document.getElementById('news-file-list');
    
    setLoading(listElement, true);
    
    fetch('/api/files')
        .then(handleResponse)
        .then(files => {
            listElement.innerHTML = '';
            
            if (files.length === 0) {
                listElement.innerHTML = '<li>No news files found</li>';
                return;
            }
            
            files.forEach(file => {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.textContent = file.title;
                a.href = '#';
                a.setAttribute('data-filename', file.filename);
                
                a.addEventListener('click', function(e) {
                    e.preventDefault();
                    loadFileContent(file.filename);
                });
                
                li.appendChild(a);
                listElement.appendChild(li);
            });
        })
        .catch(error => {
            console.error('Error:', error);
            listElement.innerHTML = `<li>Error: ${error.message}</li>`;
        })
        .finally(() => {
            setLoading(listElement, false);
        });
}

// Function to load file content
function loadFileContent(filename) {
    const contentElement = document.getElementById('file-content');
    
    showSection('file-content-section');
    setLoading(contentElement, true);
    
    fetch(`/view/${filename}`)
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => {
                    throw new Error(text || `HTTP error ${response.status}`);
                });
            }
            
            // Try to parse as JSON first
            return response.text().then(text => {
                try {
                    return { isJSON: true, data: JSON.parse(text) };
                } catch (e) {
                    // If not JSON, return as raw markdown
                    return { isJSON: false, data: text };
                }
            });
        })
        .then(result => {
            if (result.isJSON) {
                const data = result.data;
                
                // Check if we have raw content from the server
                if (data.raw_content) {
                    // Use the raw content directly
                    const title = data.title || filename.replace('.md', '').replace(/_/g, ' ');
                    const formattedContent = formatMarkdown(data.raw_content);
                    
                    contentElement.innerHTML = `
                        <h1>${title.charAt(0).toUpperCase() + title.slice(1)}</h1>
                        <div class="markdown-content">
                            ${formattedContent}
                        </div>
                    `;
                }
                // Fallback to articles format if raw content is not available
                else if (data.articles && Array.isArray(data.articles)) {
                    // Handle JSON format with articles property
                    let html = `<h1>${data.title || filename.replace('.md', '').replace(/_/g, ' ')}</h1>`;
                    html += '<div class="news-grid">';
                    
                    data.articles.forEach(article => {
                        html += `
                            <div class="news-item">
                                <h3><a href="${article.url}" target="_blank">${article.title}</a></h3>
                                <div class="source">${article.source && article.source.name ? article.source.name : 'Unknown'}</div>
                                <div class="description">${article.description || ''}</div>
                            </div>
                        `;
                    });
                    
                    html += '</div>';
                    contentElement.innerHTML = html;
                } 
                else {
                    // Handle unexpected data format
                    contentElement.innerHTML = `<div class="error">Error: Invalid data format from server</div>`;
                }
            } else {
                // Handle markdown format directly
                const title = filename.replace('.md', '').replace(/_/g, ' ');
                const formattedContent = formatMarkdown(result.data);
                
                contentElement.innerHTML = `
                    <h1>${title.charAt(0).toUpperCase() + title.slice(1)}</h1>
                    <div class="markdown-content">
                        ${formattedContent}
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            contentElement.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        })
        .finally(() => {
            setLoading(contentElement, false);
        });
}

// Helper function to format markdown content for display
function formatMarkdown(markdown) {
    if (!markdown || typeof markdown !== 'string') {
        console.error('Invalid markdown content:', markdown);
        return '<p>Error displaying content. Please try again later.</p>';
    }
    
    try {
        // Basic markdown formatting
        let html = markdown
            // Headers
            .replace(/^# (.*$)/gm, '<h1>$1</h1>')
            .replace(/^## (.*$)/gm, '<h2>$1</h2>')
            .replace(/^### (.*$)/gm, '<h3>$1</h3>')
            // Bold
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Italic
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Links
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
            // Images
            .replace(/!\[([^\]]+)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" class="article-image">')
            // Lists
            .replace(/^\s*\*\s(.*$)/gm, '<li>$1</li>')
            .replace(/(<li>.*<\/li>\n)+/g, '<ul>$&</ul>')
            // Paragraphs
            .replace(/\n\n/g, '</p><p>')
            // Horizontal rules
            .replace(/^---$/gm, '<hr>');
        
        // Wrap in paragraphs if not already
        if (!html.startsWith('<h1>') && !html.startsWith('<p>')) {
            html = `<p>${html}</p>`;
        }
        
        // Fix any double paragraph tags
        html = html.replace(/<\/p><p><\/p><p>/g, '</p><p>');
        
        return html;
    } catch (error) {
        console.error('Error formatting markdown:', error);
        return `<p>${markdown}</p>`;
    }
}

// Function to load sources
function loadSources() {
    const sourcesElement = document.getElementById('sources-content');
    setLoading(sourcesElement, true);
    
    loadFileContent('sources.md');
}

// Function to load top headlines
function loadTopHeadlines(country, category) {
    const resultsElement = document.getElementById('headlines-results');
    setLoading(resultsElement, true);
    
    fetch(`/api/headlines?country=${country}&category=${category}&pageSize=10`)
        .then(handleResponse)
        .then(data => {
            displayNewsGrid(data.articles, resultsElement);
        })
        .catch(error => {
            console.error('Error:', error);
            resultsElement.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        })
        .finally(() => {
            setLoading(resultsElement, false);
        });
}

// Function to load RSS feed from source
function loadRSSFeed(source, containerElement) {
    setLoading(containerElement, true);
    
    fetch(`/api/rss?source=${source}`)
        .then(handleResponse)
        .then(data => {
            displayNewsGrid(data.items, containerElement);
        })
        .catch(error => {
            console.error('Error:', error);
            containerElement.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        })
        .finally(() => {
            setLoading(containerElement, false);
        });
}

// Function to load recent headlines for welcome page
function loadRecentHeadlines() {
    const welcomeNewsElement = document.getElementById('welcome-news');
    if (!welcomeNewsElement) return;
    
    setLoading(welcomeNewsElement, true);
    
    fetch('/api/recent')
        .then(handleResponse)
        .then(data => {
            displayNewsGrid(data.articles, welcomeNewsElement);
        })
        .catch(error => {
            console.error('Error:', error);
            welcomeNewsElement.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        })
        .finally(() => {
            setLoading(welcomeNewsElement, false);
        });
}

// Function to run a search query
function runSearch(query, searchIn, language, fromDate, toDate, sortBy) {
    const resultsElement = document.getElementById('search-results');
    setLoading(resultsElement, true);
    
    // Build URL
    let url = `/api/search?q=${encodeURIComponent(query)}`;
    
    if (searchIn && searchIn !== 'all') {
        url += `&searchIn=${searchIn}`;
    }
    
    if (language) {
        url += `&language=${language}`;
    }
    
    if (fromDate) {
        url += `&from=${fromDate}`;
    }
    
    if (toDate) {
        url += `&to=${toDate}`;
    }
    
    if (sortBy) {
        url += `&sortBy=${sortBy}`;
    }
    
    fetch(url)
        .then(handleResponse)
        .then(data => {
            displayNewsGrid(data.articles, resultsElement);
        })
        .catch(error => {
            console.error('Error:', error);
            resultsElement.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        })
        .finally(() => {
            setLoading(resultsElement, false);
        });
}

// Function to load news for a specific category
function loadCategoryNews(category) {
    const contentElement = document.getElementById('file-content');
    showSection('file-content-section');
    setLoading(contentElement, true);
    
    // Map categories to filenames
    const categoryFiles = {
        'economy': 'economy.md',
        'environment': 'environment.md',
        'international': 'international.md',
        'governance': 'governance.md',
        'polity': 'polity.md',
        'science': 'science.md',
        'india': 'india_news.md',
        'business': 'business_headlines.md',
        'global': 'global_headlines.md',
        'all': 'sources.md'
    };
    
    const filename = categoryFiles[category] || 'sources.md';
    loadFileContent(filename);
}

// Helper function to get keywords for categories
function getCategoryKeywords(category) {
    const keywords = {
        'economy': ['economy', 'economic', 'finance', 'budget', 'gdp', 'fiscal', 'monetary', 'inflation', 'market'],
        'environment': ['environment', 'climate', 'wildlife', 'pollution', 'conservation', 'biodiversity', 'forest', 'emission'],
        'international': ['international', 'diplomatic', 'global', 'treaty', 'un', 'bilateral', 'multilateral', 'foreign policy'],
        'governance': ['governance', 'policy', 'scheme', 'initiative', 'mission', 'program', 'administration', 'reform'],
        'polity': ['polity', 'constitution', 'law', 'supreme court', 'parliament', 'democracy', 'federalism', 'judiciary'],
        'science': ['science', 'technology', 'innovation', 'research', 'discovery', 'space', 'digital', 'ai', 'biotech']
    };
    
    return keywords[category] || [];
}

// Function to display news in grid format
function displayNewsGrid(newsItems, container) {
    container.innerHTML = '';
    
    if (!newsItems || newsItems.length === 0) {
        container.innerHTML = '<div class="no-results">No news items found</div>';
        return;
    }
    
    const grid = document.createElement('div');
    grid.className = 'news-grid';
    
    newsItems.forEach(item => {
        const article = item.article || item;  // Handle different API formats
        
        const newsItem = document.createElement('div');
        newsItem.className = 'news-item';
        
        // Create title
        const title = document.createElement('h3');
        const titleLink = document.createElement('a');
        titleLink.textContent = article.title;
        titleLink.href = article.url || '#';
        titleLink.target = '_blank';
        title.appendChild(titleLink);
        
        // Create source
        const source = document.createElement('div');
        source.className = 'source';
        source.textContent = (article.source && article.source.name) ? article.source.name : article.source || 'Unknown';
        
        // Create description
        const description = document.createElement('div');
        description.className = 'description';
        description.textContent = article.description || '';
        
        // Add view article button
        const viewButton = document.createElement('button');
        viewButton.textContent = 'View Details';
        viewButton.className = 'view-article';
        viewButton.addEventListener('click', function() {
            displayArticle(article);
        });
        
        // Add elements to news item
        newsItem.appendChild(title);
        newsItem.appendChild(source);
        newsItem.appendChild(description);
        newsItem.appendChild(viewButton);
        
        // Set up feedback on this item
        setupItemFeedback(newsItem, article.url);
        
        grid.appendChild(newsItem);
    });
    
    container.appendChild(grid);
}

// Function to display a single article in detail view
function displayArticle(article) {
    const articleView = document.getElementById('article-view');
    articleView.innerHTML = '';
    
    // Create article container
    const articleContainer = document.createElement('div');
    articleContainer.className = 'article';
    
    // Create headline
    const headline = document.createElement('h2');
    headline.className = 'headline';
    headline.textContent = article.title;
    
    // Create byline
    const byline = document.createElement('div');
    byline.className = 'byline';
    byline.innerHTML = `<span>Source: ${(article.source && article.source.name) ? article.source.name : article.source || 'Unknown'}</span>
                        <span>Published: ${new Date(article.publishedAt).toLocaleString()}</span>`;
    
    // Create content
    const content = document.createElement('div');
    content.className = 'article-content';
    content.innerHTML = article.content || article.description || '';
    
    // Create source link
    const sourceLink = document.createElement('div');
    sourceLink.className = 'source-link';
    sourceLink.innerHTML = `<a href="${article.url}" target="_blank">Read full article at source</a>`;
    
    // Set up feedback for this article
    const feedbackDiv = document.createElement('div');
    feedbackDiv.className = 'article-feedback';
    setupItemFeedback(feedbackDiv, article.url);
    
    // Add back button
    const backButton = document.createElement('button');
    backButton.className = 'back-button';
    backButton.textContent = 'Back to Results';
    backButton.addEventListener('click', function() {
        history.back();
    });
    
    // Add everything to container
    articleContainer.appendChild(headline);
    articleContainer.appendChild(byline);
    articleContainer.appendChild(content);
    articleContainer.appendChild(sourceLink);
    articleContainer.appendChild(feedbackDiv);
    articleContainer.appendChild(backButton);
    
    // Add to view and show it
    articleView.appendChild(articleContainer);
    showSection('article-view');
}

// Set up feedback system
function setupFeedbackSystem() {
    // Load any saved feedback data
    fetch('/api/feedback')
        .then(handleResponse)
        .then(data => {
            appState.feedbackData = data;
        })
        .catch(error => {
            console.error('Error loading feedback:', error);
        });
}

// Set up feedback UI for individual items
function setupItemFeedback(container, url) {
    if (!url) return;
    
    const feedbackDiv = document.createElement('div');
    feedbackDiv.className = 'article-feedback';
    
    const thumbsUp = document.createElement('button');
    thumbsUp.textContent = '👍 Helpful';
    thumbsUp.className = 'thumb-up';
    thumbsUp.setAttribute('data-url', url);
    thumbsUp.setAttribute('data-rating', 'up');
    
    const thumbsDown = document.createElement('button');
    thumbsDown.textContent = '👎 Not Helpful';
    thumbsDown.className = 'thumb-down';
    thumbsDown.setAttribute('data-url', url);
    thumbsDown.setAttribute('data-rating', 'down');
    
    // Check if we already have feedback for this URL
    if (appState.feedbackData[url]) {
        if (appState.feedbackData[url] === 'up') {
            thumbsUp.classList.add('active');
        } else if (appState.feedbackData[url] === 'down') {
            thumbsDown.classList.add('active');
        }
    }
    
    // Add event listeners
    thumbsUp.addEventListener('click', function() {
        // Remove active class from all buttons
        thumbsUp.parentElement.querySelectorAll('button').forEach(btn => btn.classList.remove('active'));
        
        // Add active class to this button
        this.classList.add('active');
        
        // Save feedback
        appState.feedbackData[url] = 'up';
        saveFeedback();
    });
    
    thumbsDown.addEventListener('click', function() {
        // Remove active class from all buttons
        thumbsDown.parentElement.querySelectorAll('button').forEach(btn => btn.classList.remove('active'));
        
        // Add active class to this button
        this.classList.add('active');
        
        // Save feedback
        appState.feedbackData[url] = 'down';
        saveFeedback();
    });
    
    feedbackDiv.appendChild(thumbsUp);
    feedbackDiv.appendChild(thumbsDown);
    
    container.appendChild(feedbackDiv);
}

// Function to save feedback
function saveFeedback() {
    fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(appState.feedbackData)
    }).catch(error => console.error('Error saving feedback:', error));
}

// Function to save preferences
function savePreferences() {
    localStorage.setItem('upsNewsPreferences', JSON.stringify({
        selectedCategory: appState.selectedCategory,
        countryPreference: appState.countryPreference,
        lastSearchQuery: appState.lastSearchQuery
    }));
}

// Function to load saved preferences
function loadSavedPreferences() {
    try {
        const savedPrefs = localStorage.getItem('upsNewsPreferences');
        if (savedPrefs) {
            const prefs = JSON.parse(savedPrefs);
            
            // Restore selected category
            if (prefs.selectedCategory) {
                appState.selectedCategory = prefs.selectedCategory;
                
                // Update category UI
                const categoryLinks = document.querySelectorAll('#category-list a');
                categoryLinks.forEach(link => {
                    if (link.getAttribute('data-category') === prefs.selectedCategory) {
                        link.parentElement.classList.add('active');
                    } else {
                        link.parentElement.classList.remove('active');
                    }
                });
            }
            
            // Restore country preference
            if (prefs.countryPreference) {
                appState.countryPreference = prefs.countryPreference;
                const countrySelect = document.getElementById('country');
                if (countrySelect) {
                    countrySelect.value = prefs.countryPreference;
                }
            }
            
            // Restore last search query
            if (prefs.lastSearchQuery) {
                appState.lastSearchQuery = prefs.lastSearchQuery;
                const searchInput = document.getElementById('search-query');
                if (searchInput) {
                    searchInput.value = prefs.lastSearchQuery;
                }
            }
        }
    } catch (error) {
        console.error('Error loading preferences:', error);
    }
}

// Helper function to handle response
function handleResponse(response) {
    if (!response.ok) {
        return response.text().then(text => {
            throw new Error(text || `HTTP error ${response.status}`);
        });
    }
    return response.json();
}

// Helper function to show/hide loading state
function setLoading(element, isLoading) {
    // Save loading state
    appState.isLoading = isLoading;
    
    if (isLoading) {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading';
        loadingDiv.innerHTML = 'Loading...';
        element.innerHTML = '';
        element.appendChild(loadingDiv);
    }
} 

// Function to update the live clock
function updateClock() {
    const clockElement = document.getElementById('live-clock');
    if (!clockElement) return;
    
    // Create a new date object
    const now = new Date();
    
    // Format the date and time for IST (Indian Standard Time)
    const options = { 
        timeZone: 'Asia/Kolkata',
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit',
        hour12: false,
        day: '2-digit',
        month: 'short',
        year: 'numeric'
    };
    
    const formattedDateTime = now.toLocaleString('en-IN', options);
    
    // Update the clock element
    clockElement.textContent = formattedDateTime;
}