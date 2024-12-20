import schedule
import time
from main import CouponScraper
import logging
from datetime import datetime
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('coupon_scheduler.log'),
        logging.StreamHandler()
    ]
)

def run_scraper():
    try:
        logging.info("Starting daily coupon scraping...")
        scraper = CouponScraper()
        scraper.run()
        logging.info("Daily coupon scraping completed successfully")
    except Exception as e:
        logging.error(f"Error during scraping: {str(e)}")
    finally:
        # Ensure the driver is closed
        if 'scraper' in locals() and hasattr(scraper, 'driver'):
            scraper.driver.quit()

def main():
    # Log startup
    logging.info("Scheduler started")
    
    # Schedule the job to run daily at 9 AM
    schedule.every().day.at("09:00").do(run_scraper)
    
    # Also run immediately on startup
    run_scraper()
    
    # Keep the script running
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except Exception as e:
            logging.error(f"Scheduler error: {str(e)}")
            time.sleep(300)  # Wait 5 minutes on error before retrying

if __name__ == "__main__":
    main()
