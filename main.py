import os
import time
from datetime import datetime
from typing import Dict, List, Optional
import json
import pywhatkit
import schedule
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
from utils import (
    get_random_user_agent,
    load_cache,
    save_cache,
    categorize_course,
    clean_udemy_url,
    format_whatsapp_message,
    parse_expiry_date,
    load_category_cache,
    save_category_cache,
    merge_course_lists
)
from config import *
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import re
from dateutil import parser
import requests
from urllib.parse import urljoin
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)
    
config = load_config()
phone_number = config['whatsapp']['phone_number']

class CouponScraper:
    
    def __init__(self, base_url='https://www.real.discount/', max_courses=30):
        """Initialize the scraper."""
        load_dotenv()
        self.max_courses = max_courses
        self.scraped_courses = 0
        #self.driver = webdriver.Chrome() 
        self.base_url = base_url  # Ensure base_url is an attribute
        self.setup_selenium()
        # Start in full-screen mode
        self.driver.maximize_window()
        self.cache = load_cache()
        self.courses = []
        self.course_links = set()  # Initialize the course_links set

        
        # Load WhatsApp group IDs
        self.group_ids = {}
        for category in CATEGORIES:
            env_key = CATEGORIES[category]['group_id']
            group_id = os.getenv(env_key)
            if group_id:
                self.group_ids[category] = group_id
                print(f"Loaded group ID for {category}: {group_id}")

    def setup_selenium(self):
        """Setup Selenium WebDriver with proper options."""
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        
        # Try to locate Chrome executable
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
        ]
        
        chrome_binary = None
        for path in chrome_paths:
            expanded_path = os.path.expandvars(path)
            if os.path.exists(expanded_path):
                chrome_binary = expanded_path
                break
        
        if chrome_binary:
            print(f"Found Chrome binary at: {chrome_binary}")
            chrome_options.binary_location = chrome_binary
        else:
            print("Warning: Could not find Chrome binary in standard locations")
        
        # Add required Chrome options
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-software-rasterizer')
        
        try:
            print("Starting WebDriver setup...")
            
            # Get Chrome driver path and create service
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            # Use specific ChromeDriver version matching your Chrome
            driver_manager = ChromeDriverManager()
            driver_path = driver_manager.install()
            
            # Ensure we're using the correct chromedriver executable
            if driver_path.endswith('THIRD_PARTY_NOTICES.chromedriver'):
                driver_dir = os.path.dirname(driver_path)
                possible_drivers = [
                    os.path.join(driver_dir, 'chromedriver.exe'),
                    os.path.join(driver_dir, 'chromedriver-win32', 'chromedriver.exe'),
                    os.path.join(driver_dir, 'chromedriver-win64', 'chromedriver.exe')
                ]
                
                for possible_driver in possible_drivers:
                    if os.path.exists(possible_driver):
                        driver_path = possible_driver
                        break
            
            print(f"Using ChromeDriver at: {driver_path}")
            
            service = Service(executable_path=driver_path)
            print("Service created successfully")
            
            print("Initializing Chrome WebDriver...")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
            print("WebDriver setup completed successfully!")
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error setting up WebDriver: {error_msg}")
            
            # Get system information for debugging
            import platform
            system_info = f"""
            System Information:
            - OS: {platform.system()} {platform.version()}
            - Python: {platform.python_version()}
            - Architecture: {platform.architecture()[0]}
            """
            
            troubleshooting_msg = f"""
            Troubleshooting steps:
            1. Make sure Google Chrome is installed and up to date
            2. Try these steps:
               a. Uninstall Chrome and reinstall the latest version
               b. Run these commands:
                  - pip uninstall selenium webdriver-manager
                  - pip install selenium webdriver-manager --upgrade
               c. Delete the .wdm folder in your user directory
            3. System Information: {system_info}
            """
            
            raise Exception(f"Could not initialize WebDriver: {error_msg}\n{troubleshooting_msg}")
    def scrape_and_extract_courses(self):
        """Scrape courses and extract their details"""
        try:
            print("\n=== Starting Course Scraping ===")
            print(f"Loading main page: {self.base_url}")

            # Initial setup
            self.driver.maximize_window()
            self.driver.get(self.base_url)

            # Setup page
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self._handle_consent()
            self._configure_page_filters()            
            

            while True:
                course_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/offer/')]")
                print(f"\nFound {len(course_links)} course links")

                self.verify_english_content()
                    

                for index, link in enumerate(course_links, start=1):
                    try:
                        print(f"\nProcessing course {index}/{len(course_links)}")
                        # Click the course link
                        self.driver.execute_script("arguments[0].click();", link)
                        # Wait for and get article URL
                        article_url_element = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CLASS_NAME, "mt-4"))
                        )
                        article_url = article_url_element.get_attribute("href")

                        if article_url:
                            print(f"Found article URL: {article_url}")
                            self.driver.get(article_url)

                            # Extract course details
                            WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.TAG_NAME, "body"))
                            )

                            article_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                            course_details = self._extract_course_details(article_soup, article_url)
                            #navigate to udemy url to get expiry date
                            self.driver.get(article_url)
                            WebDriverWait(self.driver, 20).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-purpose='discount-expiration']"))
                            )
                            # Get expiry date with bold tag
                            expiry = None
                            expiry_elem = article_soup.find('div', class_='discount-expiration--discount-expiration--iSt-e')
                            if expiry_elem:
                                expiry_text_elem = expiry_elem.find('span', {'data-purpose': 'safely-set-inner-html:discount-expiration:expiration-text'})
                                if expiry_text_elem and expiry_text_elem.find('b'):
                                    expiry = expiry_text_elem.get_text(strip=True)
                                    print(f"Found course with bold expiry tag: {expiry}")

                            if course_details and not self._is_course_processed(course_details):
                                print(f"Adding new course: {course_details['title']}")
                                self.courses.append(course_details)

                        # Return to main page
                        self.driver.back()                        
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@href, '/offer/')]"))
                        )

                    except StaleElementReferenceException:
                        print(f"Stale element reference encountered for course {index}. Retrying...")
                        continue
                    except Exception as e:
                        print(f"Error processing course {index}: {str(e)}")
                        self.driver.get(self.base_url)
                        continue

                if not course_links:
                    print("No more courses to process.")
                    break

        except Exception as e:
            print(f"Error in scrape_and_extract_courses: {str(e)}")
    

    def _click_load_more(self):
        """Click the Load More button if available."""
        try:
            # Try to find the Load More button
            load_more = self.driver.find_element(By.CSS_SELECTOR, ".btn.btn-primary.mb-5")
            
            # Scroll just above the button to trigger loading but avoid clicking it directly
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", load_more)
            time.sleep(2)  # Wait for any animations
            
            if load_more.is_displayed() and load_more.is_enabled():
                print("Clicking Load More button")
                load_more.click()
                time.sleep(3)  # Wait for new content to load
                return True
                
        except NoSuchElementException:
            print("No Load More button found")
        except Exception as e:
            print(f"Error clicking Load More: {str(e)}")
        return False

    def _handle_consent(self):
        """Handle the cookie consent popup."""
        try:
            # Wait for consent button
            consent_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "fc-button-label"))
            )
            print("Found consent button")
            consent_button.click()
            print("Clicked consent button")
            time.sleep(2)  # Wait for popup to close
        except Exception as e:
            print(f"No consent button found or error clicking it: {str(e)}")



    def _configure_page_filters(self):
        """Configure page filters with correct selectors."""
        print("\nConfiguring page filters...")

        # Set language filter to English
        language_dropdown = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "language"))
        )
        select = Select(language_dropdown)
        select.select_by_visible_text("English")
        print("Language filter set to English")
        time.sleep(2)

        # Set free courses filter
        free_label = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "label[for='free']"))
        )
        free_label.click()
        print("Free filter applied")
        time.sleep(2)

        # Verify language filter
        selected_language = select.first_selected_option.text
        print(f"Current language filter: {selected_language}")

        # Run content verification - correct way to call the method
        is_english = self.verify_english_content()
        print(f"English content verification: {'Passed' if is_english else 'Failed'}")
    
    # Verify English courses using content check
    def verify_english_content(self):
        """Verify if the content is in English."""
        article_soup = BeautifulSoup(self.driver.page_source, 'html.parser')

        language_indicators = [
            article_soup.find('div', string=re.compile(r'Language.*English', re.IGNORECASE)),
            article_soup.find('span', string=re.compile(r'Language.*English', re.IGNORECASE)),
            article_soup.find('div', {'class': 'p-2 text-center'}, string=re.compile(r'English', re.IGNORECASE))
        ]

        if any(indicator for indicator in language_indicators):
            print("English content confirmed")
            return True

        details = article_soup.find_all('div', class_='mt-1')
        for detail in details:
            if 'english' in detail.get_text().lower():
                print("English content found in details")
                return True

        return False

    def select_language(self, language):
        """Select language from dropdown"""
        try:
            # Find and select language
            language_dropdown = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "language"))
            )
            select = Select(language_dropdown)
            select.select_by_value(language)
            time.sleep(2)  # Wait for selection to take effect
            print(f"Successfully set language to: {language}")
        except Exception as e:
            print(f"Language selection error: {str(e)}")
    
    def extract_course_length(self, article_soup):
        """Extract and validate course length."""
        try:
            # Find clock icon container
            clock_container = article_soup.find('div', class_='p-2 text-center', 
                string=lambda text: text and 'fa-clock' in text)

            if clock_container:
                duration_elem = clock_container.find('div', class_='mt-1')
                if duration_elem:
                    length_text = duration_elem.get_text(strip=True)
                    # Standardize format
                    length_text = length_text.replace('hr', ' hr').strip()
                    print(f"Course length found: {length_text}")
                    return length_text

            print("No valid course length found")
            return None

        except Exception as e:
            print(f"Error extracting course length: {e}")
            return None

    def _extract_course_details(self, article_soup, article_url):
        """Extract course details from an article."""
        try:
            

            # Price check
            price_elem = article_soup.find('span', class_='ml-1')
            if not price_elem or price_elem.get_text().strip() != '0':
                print("Skipping non-free course")
                return None

            # Get course title
            title_container = article_soup.find('div', class_='row mt-3')
            if not title_container or not (link_elem := title_container.find('a')):
                print("Title container or link not found")
                return None

            title = link_elem.get_text(strip=True)
            print(f"Found course: {title}")

            # Get Udemy URL
            print(f"Getting Udemy URL for: {title}")
            udemy_url = self._get_udemy_url(article_url)
            if not udemy_url:
                print("Failed to get Udemy URL")
                return None

            # Extract coupon code
            coupon_code_match = re.search(r'couponCode=([A-Z0-9]+)', article_url)
            coupon_code = coupon_code_match.group(1) if coupon_code_match else None

            # Extract course length 
            length_text = self.extract_course_length(article_soup)
            # Extract remaining days from expiry text
            expiry_days = None
            expiry_elem = self.driver.find_element(By.CSS_SELECTOR, 
                "span[data-purpose='safely-set-inner-html:discount-expiration:expiration-text'] b"
            )

            if expiry_elem:
                days_text = expiry_elem.text
                # Extract just the number from "4 jours"
                expiry_days = days_text.split()[0]
                print(f"Days remaining to claim: {expiry_days}")


            course_details = {
                'title': title,
                'original_price': '0',
                'current_price': "0",
                'course_length': length_text,
                'expired in': expiry_days,
                'url': udemy_url,
                'coupon_code': coupon_code
            }

            print(f"Successfully extracted details for: {title}")
            return course_details

        except Exception as e:
            print(f"Error extracting course details: {str(e)}")
            return None

    def _get_udemy_url(self, course_page_url: str) -> Optional[str]:
        """Visit the course page and get the Udemy URL."""
        try:
            # Load the course page
            self.driver.get(course_page_url)
            time.sleep(5)  # Initial wait for page load
            
            # Wait for the enroll button
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "btn-lg"))
                )
            except TimeoutException:
                print(f"Enroll button not found on page: {course_page_url}")
                return None
            
            # Find and click the enroll button
            enroll_button = self.driver.find_element(By.CLASS_NAME, "btn-lg")
            if not enroll_button:
                print("Enroll button not found")
                return None
            
            # Click the button
            self.driver.execute_script("arguments[0].click();", enroll_button)
            
            # Wait for the redirect or new window
            time.sleep(10)  # Give time for redirect/new window
            
            # Handle potential new window
            windows = self.driver.window_handles
            if len(windows) > 1:
                self.driver.switch_to.window(windows[-1])
            
            # Get the current URL which should be the Udemy course page
            udemy_url = self.driver.current_url
            
            # Clean the URL
            cleaned_url = clean_udemy_url(udemy_url)
            
            # Switch back to the main window if necessary
            if len(windows) > 1:
                self.driver.close()  # Close the Udemy window
                self.driver.switch_to.window(windows[0])  # Switch back to main window
            
            return cleaned_url
            
        except Exception as e:
            print(f"Error getting Udemy URL: {str(e)}")
            return None

    def _detect_category(self, title: str, description: str) -> Optional[str]:
        """Detect the category of a course based on its title and description."""
        title_lower = title.lower()
        desc_lower = description.lower()
        
        # Define category keywords
        category_keywords = {
            'cybersecurity': ['security', 'cyber', 'hacking', 'penetration testing', 'encryption', 'firewall'],
            'web_design': ['web design', 'css', 'html', 'ui/ux', 'responsive design'],
            'backend': ['backend', 'django', 'flask', 'node.js', 'express.js', 'php', 'laravel'],
            'fullstack': ['full stack', 'fullstack', 'mern', 'mean'],
            'app_development': ['app development', 'android', 'ios', 'swift', 'kotlin'],
            'mobile': ['mobile', 'react native', 'flutter', 'ionic'],
            'cloud': ['aws', 'azure', 'cloud', 'devops', 'docker', 'kubernetes'],
            'quantum': ['quantum', 'qiskit', 'quantum computing'],
            'seo': ['seo', 'search engine optimization', 'google analytics'],
            'software': ['software', 'programming', 'java', 'c++', 'python'],
            'AI': ['ai', 'artificial intelligence', 'machine learning', 'deep learning', 'neural networks'],
            'crypto': ['crypto', 'blockchain', 'bitcoin', 'ethereum', 'nft'],
            'marketing': ['marketing', 'digital marketing', 'social media', 'advertising'],
            'design': ['design', 'photoshop', 'illustrator', 'graphic design'],
            'personal_development': ['personal development', 'leadership', 'management', 'productivity']
        }
        
        # Check each category's keywords
        max_matches = 0
        best_category = None
        
        for category, keywords in category_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in title_lower or keyword in desc_lower)
            if matches > max_matches:
                max_matches = matches
                best_category = category
        
        return best_category if max_matches > 0 else None

    def process_courses(driver, courses):
        for index, course in enumerate(courses):
            retries = 3  # Number of retries for stale element
            for attempt in range(retries):
                try:
                    print(f"Processing course {index + 1}/{len(courses)}")

                    # Locate the course element (example)
                    course_element = driver.find_element_by_xpath(course['xpath'])  # Adjust as necessary

                    # Perform actions on the course element
                    # Example: course_element.click() or extract information

                    break  # Exit the retry loop if successful
                except StaleElementReferenceException:
                    print(f"Stale element reference encountered for course {index + 1}. Retrying...")
                    time.sleep(1)  # Optional: wait before retrying
                    # Re-locate the course element if necessary
                    course_element = driver.find_element_by_xpath(course['xpath'])  # Re-locate
            else:
                print(f"Failed to process course {index + 1} after {retries} attempts.")

        courses = [{'xpath': '...'}, {'xpath': '...'}, ...]  # List of course elements

    def _process_courses(self):
        """Process found courses and send to WhatsApp."""
        if not self.courses:
            print("No courses found.")
            return

        # Group courses by category
        categorized_courses = self._group_courses_by_category(self.courses)

        for category, courses in categorized_courses.items():
            if category not in self.group_ids:
                continue

            # Load existing courses for this category
            existing_courses = load_category_cache(category)

            # Merge new courses with existing ones
            merged_courses = merge_course_lists(existing_courses, courses)

            # Save updated course list for this category
            save_category_cache(category, merged_courses)

            # Format message with merged courses
            message = format_whatsapp_message(merged_courses, category, CATEGORIES[category]['template'])

            if message:
                print(f"Sending message for category: {category}")
                self.send_whatsapp_message(self.group_ids[category], message)

            # Mark all courses as processed in the main cache
            for course in courses:
                self._mark_course_processed(course)

    def process_and_send_courses(self):
        self.driver.get(self.base_url)  # Open the target webpage
        time.sleep(2)  # Wait for the page to load
        scraper._handle_consent()  # Handle consent if needed
        scraper._configure_page_filters()  # Configure page filters
        # Language check
        self.verify_english_content()

        while self.scraped_courses < self.max_courses:
            # Find course elements
            course_elements = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/offer/')]")        
            for course_element in course_elements:
                article_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Extract course data
                course_title = course_element.find_element(
                    By.XPATH,
                    ".//h3[contains(@class, 'ml-3')]"
                ).text
                # Extract old price
                course_price_old = None
                if price_old_container := article_soup.find('span', class_='card-price-full'):
                    course_price_old = price_old_container.get_text(strip=True)
                    print(f"Original price found: {course_price_old}")

                # Extract new price and validate it's free
                course_price_new = None
                # First find the dollar sign icon
                dollar_icon = article_soup.find('i', class_='fas fa-dollar-sign')
                if dollar_icon:
                    # Navigate to price container
                    price_container = dollar_icon.find_parent('div').find('div', class_='ml-1')
                    if price_container:
                        free_price = price_container.find('span')  # Get first span with '0$'
                        if free_price:
                            price_text = free_price.get_text(strip=True)
                            cleaned_price = price_text.replace('$', '').strip()
                            if cleaned_price == '0':
                                course_price_new = '0'
                                print("Confirmed free course")

                                # Extract original price
                                original_price = price_container.find('span', class_='card-price-full')
                                if original_price:
                                    course_price_old = original_price.get_text(strip=True)
                                    print(f"Original price was: {course_price_old}")

                time_completion = None
                if duration_container := article_soup.find('div', class_='p-2 text-center'):
                    if duration_elem := duration_container.find('div', class_='mt-1'):
                        time_completion = duration_elem.get_text(strip=True)
                course_category = None
                if category_container := article_soup.find('div', class_='row'):
                    if category_elem := category_container.find('div', class_='ml-3'):
                        course_category = category_elem.get_text(strip=True)
                

                if self.scraped_courses >= self.max_courses:
                    print("Reached the maximum number of courses to scrape.")
                    return

                try:
                    # Extract course information
                    course_link = course_element.get_attribute("href")

                    if course_link not in self.course_links:
                        self.course_links.add(course_link)
                        # Click to open course page
                        self.driver.execute_script("arguments[0].click();", course_element)
                        time.sleep(5)

                        # Get coupon URL of udemy page
                        coupon_element = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, '//div[@class="mt-4"]//a[@target="_blank"]'))
                        )
                        coupon_url = coupon_element.get_attribute('href')
                        # Navigate to coupon URL
                        self.driver.get(coupon_url)
                        WebDriverWait(self.driver, 20).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "span[data-purpose='safely-set-inner-html:discount-expiration:expiration-text'] b"))
                        )
                        expiry_days = None
                        expiry_elem = self.driver.find_element(By.CSS_SELECTOR, 
                        "span[data-purpose='safely-set-inner-html:discount-expiration:expiration-text'] b"
                        )                    
                        #article_soup.find('div', class_='discount-expiration--discount-expiration--iSt-e')
                        if expiry_elem:
                            days_text = expiry_elem.text
                            # Extract just the number from "4 jours"
                            expiry_days = days_text.split()[0]
                            print(f"Days remaining to claim: {expiry_days}")
                        # Print to console
                        print(f"Processing course {self.scraped_courses + 1}/{self.max_courses}:")
                        print(f"Title: {course_title}")
                        print(f"OldPrice: {course_price_old}")
                        print(f"NewPrice: {course_price_new}")
                        print(f"Time to complete: {time_completion}")
                        print(f"Link scraped: {course_link}")
                        print(f"Coupon: {coupon_url}\n")
                        print(f"expire in: {expiry_days}")

                        self.scraped_courses += 1

                        # Return to main page
                        self.driver.back()
                        time.sleep(2)

                except StaleElementReferenceException:
                    print("Refreshing stale element...")
                    time.sleep(1)
                    continue

                except Exception as e:
                    print(f"Error processing course: {str(e)}")
                    continue

            # Try to load more courses
            if not self._click_load_more():
                print("No more courses to load.")
                break

        print(f"Completed scraping {self.scraped_courses} courses.")


    def run_scheduled(self):
        """Run the scraper on a schedule."""
        schedule.every(SCHEDULE_INTERVAL).hours.do(self.process_and_send_courses)
        
        while True:
            schedule.run_pending()
            time.sleep(1)

    def cleanup(self):
        """Clean up resources."""
        self.driver.quit()

    def _is_course_processed(self, course):
        """Check if course is already processed."""
        url = course.get('url', '')
        return url in self.cache.get('processed_courses', [])

    def _mark_course_processed(self, course):
        """Mark course as processed."""
        url = course.get('url', '')
        coupon_code = course.get('coupon_code', '')

        # Create a processed course entry
        processed_course_entry = {
            'url': url,
            'coupon_code': coupon_code,
            'udemy_url': course.get('udemy_url', '')
        }

        if 'processed_courses' not in self.cache:
            self.cache['processed_courses'] = []

        # Check if the course is already processed
        if processed_course_entry not in self.cache['processed_courses']:
            self.cache['processed _courses'].append(processed_course_entry)
            print(f"Marked course as processed: {url}")
        else:
            print(f"Course already processed: {url}")

    def send_whatsapp_message(self, phone_number: str, message: str):
        """Send WhatsApp message using pywhatkit."""
        try:
            # Get current hour and minute
            now = datetime.now()
            # Add 2 minutes to current time to ensure WhatsApp Web loads
            send_time = now.replace(minute=now.minute + 2)
            
            pywhatkit.sendwhatmsg(
                phone_number,
                message,
                send_time.hour,
                send_time.minute,
                wait_time=20,
                tab_close=True
            )
            print(f"WhatsApp message scheduled for {send_time.hour}:{send_time.minute}")
            return True
        except Exception as e:
            print(f"Error sending WhatsApp message: {str(e)}")
            return False

    def _group_courses_by_category(self, courses):
        """Group courses by their category."""
        grouped_courses = {}
        for course in courses:
            category = course.get('category', 'Uncategorized')
            if category not in grouped_courses:
                grouped_courses[category] = []
            grouped_courses[category].append(course)
        return grouped_courses
    def output_processed_courses(self):
        """Output the processed courses in JSON format."""
        processed_courses_json = {
            "processed_courses": self.cache.get('processed_courses', [])
        }

        print(json.dumps(processed_courses_json, indent=4))

if __name__ == "__main__":
    scraper = CouponScraper(max_courses=30)
    try:
        # Run once immediately
        scraper.process_and_send_courses()
        # Then start the schedule
        scraper.run_scheduled()
    except KeyboardInterrupt:
        print("\nStopping scraper...")
    finally:
        scraper.cleanup()
