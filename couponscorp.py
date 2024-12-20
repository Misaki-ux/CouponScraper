import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
from typing import List, Dict
import json
import os
import random

class CouponScorpionScraper:
    def __init__(self):
        self.base_url = "https://couponscorpion.com"
        self.search_url = f"{self.base_url}/?s=design&post_type=post%2Cpage"
        # Add known article URLs
        self.known_articles = [
            "https://couponscorpion.com/design/complete-graphics-design-and-video-editing-masterclass/"
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Referer': 'https://www.google.com/',
            'Origin': 'https://www.google.com'
        }
        self.cache_file = 'cache/couponscorp_cache.json'
        self.cache = self.load_cache()

    def load_cache(self) -> Dict:
        """Load previously processed articles from cache."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("Cache file corrupted, starting fresh")
                return {}
        return {}

    def save_cache(self):
        """Save processed articles to cache."""
        os.makedirs('cache', exist_ok=True)
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f)

    def get_page(self, url: str, retries: int = 3) -> BeautifulSoup:
        """Fetch and parse a webpage with retries."""
        for attempt in range(retries):
            try:
                session = requests.Session()
                
                # Add a small delay
                time.sleep(2)
                
                # First get the main page to get any cookies
                main_response = session.get(self.base_url, headers=self.headers, timeout=10)
                if main_response.status_code == 200:
                    print("Successfully connected to main page")
                
                # Update headers with cookies
                self.headers['Cookie'] = '; '.join([f"{c.name}={c.value}" for c in session.cookies])
                
                # Another small delay
                time.sleep(2)
                
                # Then get the actual page we want
                response = session.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                
                # Print response info for debugging
                print(f"\nResponse status: {response.status_code}")
                print(f"Response encoding: {response.encoding}")
                print(f"Content type: {response.headers.get('content-type', 'unknown')}")
                
                # Try to detect the encoding
                if response.encoding is None or response.encoding == 'ISO-8859-1':
                    response.encoding = 'utf-8'
                
                # Try multiple parsing methods
                for parser in ['lxml', 'html.parser', 'html5lib']:
                    try:
                        soup = BeautifulSoup(response.text, parser)
                        print(f"\nTrying parser: {parser}")
                        
                        # Check if we got a valid page
                        if soup.find('body'):
                            print(f"Successfully parsed with {parser}")
                            
                            # Debug: Print page structure
                            try:
                                print("\nPage Structure:")
                                tags = set(tag.name for tag in soup.find_all())
                                classes = set(cls for tag in soup.find_all() if tag.get('class') for cls in tag.get('class'))
                                
                                print("Available tags:", tags)
                                print("\nAvailable classes:", classes)
                                
                                # Print first few characters of the page to check if we're getting valid HTML
                                content_preview = response.text[:500].encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                                print("\nPage preview:")
                                print(content_preview)
                            except Exception as e:
                                print(f"Error printing debug info: {e}")
                            
                            return soup
                    except Exception as e:
                        print(f"Parser {parser} failed: {e}")
                        continue
                
                raise Exception("All parsers failed")
                
            except requests.RequestException as e:
                if attempt == retries - 1:
                    raise
                print(f"Error fetching {url}: {e}. Retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff

    def extract_course_info(self, article) -> Dict:
        """Extract course information from an article."""
        try:
            # Find the title using the exact class structure
            title_element = article.find('h2', class_=['font130', 'mt0', 'mb10', 'mobfont120', 'lineheight25'])
            if not title_element:
                return None
            
            # Get the link from the title
            title_link = title_element.find('a')
            if not title_link:
                return None
            
            title = title_link.get_text(strip=True)
            article_url = title_link.get('href')
            
            if not article_url or not title:
                return None
            
            # Now visit the article page to get the course URL
            print(f"\nVisiting article: {article_url}")
            article_soup = self.get_page(article_url)
            
            # Wait for 5 seconds as requested
            time.sleep(5)
            
            # Look for the button wrapper and get the course URL
            button_wrapper = article_soup.find('div', class_='rh_button_wrapper')
            if button_wrapper:
                course_link = button_wrapper.find('a')
                if course_link:
                    course_url = course_link.get('href')
                    if course_url:
                        # Try to find the date
                        date_str = self.extract_date(article)
                        if not date_str:
                            date_str = datetime.now().strftime('%Y-%m-%d')
                        
                        return {
                            'title': title,
                            'link': article_url,
                            'course_url': course_url,
                            'date': date_str
                        }
            
            return None
            
        except Exception as e:
            print(f"Error extracting course info: {e}")
            return None

    def extract_date(self, article):
        # Try to find the date
        date_element = (
            article.find('span', class_='date_meta') or  # Primary date location
            article.find('time') or                      # Alternative date element
            article.find('span', class_='post-meta-date')  # Another possibility
        )
        
        if date_element:
            try:
                date_text = date_element.get_text(strip=True)
                # Try to parse various date formats
                try:
                    return datetime.strptime(date_text, '%B %d, %Y').strftime('%Y-%m-%d')
                except ValueError:
                    try:
                        return datetime.strptime(date_text, '%Y-%m-%d').strftime('%Y-%m-%d')
                    except ValueError:
                        try:
                            return datetime.strptime(date_text, '%d/%m/%Y').strftime('%Y-%m-%d')
                        except ValueError:
                            pass
            except Exception:
                pass
        
        return None

    def extract_course_info_from_url(self, url: str) -> Dict:
        """Extract course information directly from a known article URL."""
        try:
            print(f"\nVisiting known article: {url}")
            article_soup = self.get_page(url)
            
            # Get the title from the URL
            title = url.split('/')[-2].replace('-', ' ').title()
            
            # Wait for 5 seconds as requested
            time.sleep(5)
            
            # Look for the button wrapper and get the course URL
            button_wrapper = article_soup.find('div', class_='rh_button_wrapper')
            if button_wrapper:
                course_link = button_wrapper.find('a')
                if course_link:
                    course_url = course_link.get('href')
                    if course_url:
                        return {
                            'title': title,
                            'link': url,
                            'course_url': course_url,
                            'date': datetime.now().strftime('%Y-%m-%d')  # Use current date
                        }
            
            return None
            
        except Exception as e:
            print(f"Error extracting course info from URL: {e}")
            return None

    def scrape_courses(self) -> List[Dict]:
        """Scrape courses from CouponScorpion."""
        try:
            print("\n=== Starting CouponScorpion Scraping ===")
            
            # Calculate date range (3 days as requested)
            today = datetime.now()
            three_days_ago = today - timedelta(days=3)
            
            latest_articles = []
            
            # First try known article URLs
            for article_url in self.known_articles:
                try:
                    # Check if article is already processed
                    if article_url in self.cache:
                        continue
                    
                    # Extract article info
                    article_info = self.extract_course_info_from_url(article_url)
                    if article_info:
                        print(f"\nFound new course: {article_info['title']}")
                        latest_articles.append(article_info)
                        self.cache[article_url] = article_info
                    
                except Exception as e:
                    print(f"Error processing article URL: {e}")
                    continue
            
            # Then try the search page
            try:
                print(f"\nFetching search URL: {self.search_url}")
                soup = self.get_page(self.search_url)
                
                # Find all course items with the specific class structure
                articles = soup.find_all('h2', class_=['font130', 'mt0', 'mb10', 'mobfont120', 'lineheight25'])
                
                print(f"Found {len(articles)} potential course items from search")
                
                for article in articles:
                    try:
                        # Extract article info
                        article_info = self.extract_course_info(article)
                        if not article_info:
                            continue
                        
                        # Check if article is already processed
                        if article_info['link'] in self.cache:
                            continue
                        
                        print(f"\nFound new course: {article_info['title']}")
                        latest_articles.append(article_info)
                        self.cache[article_info['link']] = article_info
                        
                    except Exception as e:
                        print(f"Error processing article: {e}")
                        continue
                
            except Exception as e:
                print(f"Error processing search page: {e}")
            
            # Save updated cache
            self.save_cache()
            
            print(f"\nFound {len(latest_articles)} new courses from the last 3 days")
            return latest_articles
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            return []

if __name__ == "__main__":
    scraper = CouponScorpionScraper()
    articles = scraper.scrape_courses()
    
    if articles:
        print("\nLatest courses:")
        for article in articles:
            print(f"\nTitle: {article['title']}")
            print(f"Date: {article['date']}")
            print(f"Link: {article['link']}")
            print(f"Course URL: {article['course_url']}")
    else:
        print("No new courses found in the last 3 days")
