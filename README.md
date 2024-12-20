# Real.Discount Coupon Scraper with WhatsApp Integration

An automated scraping system that collects free course coupons from Real.discount and distributes them to specific WhatsApp groups based on course categories.

## Features

- **Automated Scraping**: Scrapes course coupons from Real.discount every 24 hours
- **Smart Categorization**: Automatically categorizes courses into specific domains
- **WhatsApp Integration**: Sends formatted course updates to dedicated WhatsApp groups
- **Cache Management**: Stores courses in JSON files by category and prevents duplicates
- **Rate Limiting**: Implements delays between requests and messages to avoid blocking
- **Error Handling**: Robust error handling and retry mechanisms for reliability

## Supported Categories

The scraper supports multiple course categories, each with its own WhatsApp group:
- Personal Development
- Cybersecurity
- Cryptocurrency
- Digital Marketing
- Backend Development
- Web Design
- Graphic Design
- Full Stack Development
- App Development
- Mobile Development
- Cloud Computing
- Quantum Computing
- SEO
- Software Development
- Artificial Intelligence

## Requirements

1. Python 3.8 or higher
2. Chrome browser installed
3. Dependencies from requirements.txt
4. WhatsApp Web access
5. Internet connection

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd couponscraper_wsap
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a .env file with your WhatsApp group IDs:
   ```env
   PERSONAL_DEVELOPMENT_GROUP_ID=your_group_id
   CYBERSECURITY_GROUP_ID=your_group_id
   CRYPTO_GROUP_ID=your_group_id
   # Add other group IDs...
   ```

## Configuration

### Main Configuration (config.py)
- Course categories and their keywords
- WhatsApp message templates
- Scraping intervals and delays
- Rate limiting settings

### Cache Management
- Courses are stored in category-specific JSON files
- Located in `cache/categories/` directory
- Prevents duplicate course sharing

## Usage

### Running the Scraper

1. Start the main script:
   ```bash
   python main.py
   ```

2. For scheduled operation:
   ```bash
   python schedule_daily.py
   ```

### Operation Flow

1. **Initialization**:
   - Loads configuration and environment variables
   - Sets up Chrome WebDriver
   - Initializes cache system

2. **Scraping Process**:
   - Visits Real.discount
   - Applies filters (English, Free courses, Latest)
   - Scrolls page to load all content
   - Extracts course information

3. **Processing**:
   - Categorizes courses based on title and description
   - Checks for duplicates in cache
   - Formats course information

4. **Distribution**:
   - Groups courses by category
   - Formats WhatsApp messages
   - Sends to appropriate groups
   - Updates cache

## Message Format

Each course notification includes:
- Course Title
- Original Price vs Current Price (Free)
- Course Duration
- Certification Status
- Coupon Code
- Expiration Date
- Direct Enrollment Link

## Maintenance

### Regular Tasks
- Monitor logs for errors
- Clear old cache files periodically
- Update category keywords as needed
- Check WhatsApp group IDs validity

### Troubleshooting
- Check Chrome WebDriver compatibility
- Verify WhatsApp Web connection
- Monitor Real.discount website changes
- Review rate limiting settings

## Error Handling

The system includes robust error handling for:
- Network connectivity issues
- Website structure changes
- WhatsApp connection problems
- Rate limiting and blocking
- Cache file corruption

## Contributing

Feel free to contribute by:
- Adding new categories
- Improving course detection
- Enhancing message formatting
- Optimizing scraping performance
- Adding new features

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational purposes only. Ensure you comply with Real.discount's terms of service and WhatsApp's usage policies.
