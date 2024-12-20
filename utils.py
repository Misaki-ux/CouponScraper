"""Utility functions for the coupon scraper."""
import json
import os
from datetime import datetime
from fake_useragent import UserAgent
from typing import Dict, List, Optional, Tuple


def get_random_user_agent() -> str:
    """Generate a random user agent string."""
    ua = UserAgent()
    return ua.random

def load_cache() -> Dict:
    """Load the cache of processed courses."""
    if os.path.exists('cache/processed_courses.json'):
        with open('cache/processed_courses.json', 'r') as f:
            return json.load(f)
    return {}

def save_cache(cache: Dict) -> None:
    """Save the cache of processed courses."""
    os.makedirs('cache', exist_ok=True)
    with open('cache/processed_courses.json', 'w') as f:
        json.dump(cache, f)

def categorize_course(title: str, description: str, categories: Dict) -> Tuple[str, int, List[str]]:
    """
    Categorize a course based on its title and description.
    Returns a tuple of (category, confidence_score, matching_keywords)
    """
    title_desc = (title + ' ' + description).lower()
    words = set(title_desc.split())
    
    # Store matches with their confidence scores
    matches = []
    
    for category, data in categories.items():
        score = 0
        matched_keywords = []
        
        # Check exact keyword matches (highest priority)
        for keyword in data['keywords']:
            if keyword in title_desc:
                score += 3
                matched_keywords.append(keyword)
        
        # Check word-level matches (medium priority)
        for keyword in data['keywords']:
            keyword_words = set(keyword.split())
            if keyword_words & words:  # intersection
                score += len(keyword_words & words)
                matched_keywords.extend(list(keyword_words & words))
        
        # Title has more weight than description
        title_lower = title.lower()
        for keyword in data['keywords']:
            if keyword in title_lower:
                score += 2
                
        if score > 0:
            matches.append((category, score, matched_keywords))
    
    # Sort matches by score in descending order
    matches.sort(key=lambda x: x[1], reverse=True)
    
    if matches:
        best_match = matches[0]
        # Log the categorization decision
        print(f"Course: {title}")
        print(f"Categorized as: {best_match[0]}")
        print(f"Confidence score: {best_match[1]}")
        print(f"Matching keywords: {', '.join(best_match[2])}")
        return best_match
    
    # If no matches found, return 'other' with 0 confidence
    return ('other', 0, [])

def clean_udemy_url(url: str) -> str:
    """Extract clean Udemy URL from linksynergy or other affiliate links."""
    if 'linksynergy.com' in url:
        try:
            # Find the actual URL after 'murl=' or 'url='
            for param in ['murl=', 'url=']:
                if param in url:
                    clean_url = url.split(param)[1]
                    # Remove any additional parameters
                    if '&' in clean_url:
                        clean_url = clean_url.split('&')[0]
                    return clean_url
        except Exception as e:
            print(f"Error cleaning linksynergy URL: {str(e)}")
    return url


def format_whatsapp_message(courses: List[Dict], category: str, template: str) -> str:
    print(f"Formatting message for category: {category}")  # Debug print
    print(f"Number of courses: {len(courses)}")  # Debug print
    courses_text = []
    
    for i, course in enumerate(courses, 1):
        print(f"Processing course {i}: {course}")  # Debug print
        title = course['title'].replace('µ', '')
        hours_text = f"• Duration: {course['certification_hours']} hours\n" if course['certification_hours'] else ""
        price_text = f"• Price: {course['original_price']} → Free with coupon\n"
        expiry_text = f"• Expires: {course['expiry_date']}\n" if course['expiry_date'] else ""
        
        course_text = (
            f"{i}. *{title}*\n"
            f"{price_text}"
            f"{hours_text}"
            f"{expiry_text}"
            f"• Coupon Code: {course['coupon_code']}\n"
            f"• URL: {course['udemy_url']}\n"
        )
        courses_text.append(course_text)
    
    formatted_courses = "\n\n".join(courses_text)
    final_message = template.format(
        category=category,
        courses=formatted_courses,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    return final_message
    
    if message_parts:
        header = f"🎓 *New {category} Courses Available!*\n"
        return header + "\n".join(message_parts)
    return ""

def parse_expiry_date(date_str: Optional[str]) -> Optional[str]:
    """Parse and format expiry date string."""
    if not date_str:
        return None
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%B %d, %Y')
    except ValueError:
        return date_str

def load_category_cache(category: str) -> List[Dict]:
    """Load the cache for a specific category."""
    cache_dir = 'cache/categories'
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{category}.json")
    
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_category_cache(category: str, courses: List[Dict]) -> None:
    """Save courses for a specific category."""
    cache_dir = 'cache/categories'
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{category}.json")
    
    # Sort courses by expiry date and title
    sorted_courses = sorted(
        courses,
        key=lambda x: (
            parse_expiry_date(x.get('expiry_date', None)) or datetime.max,
            x.get('title', '').lower()
        )
    )
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(sorted_courses, f, indent=2, ensure_ascii=False)

def merge_course_lists(existing_courses: List[Dict], new_courses: List[Dict]) -> List[Dict]:
    """Merge two course lists, removing duplicates based on URL."""
    # Create a dictionary of existing courses using URL as key
    existing_dict = {course['url']: course for course in existing_courses}
    
    # Update with new courses, overwriting if same URL exists
    for course in new_courses:
        existing_dict[course['url']] = course
    
    # Convert back to list
    return list(existing_dict.values())
