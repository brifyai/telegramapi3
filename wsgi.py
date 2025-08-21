#!/usr/bin/env python3
"""
WSGI entry point for Heroku deployment
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging for Heroku
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

try:
    # Load environment variables
    load_dotenv()
    
    # Import the Flask app
    from web_interface import app
    
    logger.info("Flask application loaded successfully")
    
    # Ensure required environment variables are set
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.warning(f"Missing environment variables: {missing_vars}")
    else:
        logger.info("All required environment variables are set")
        
except Exception as e:
    logger.error(f"Failed to load Flask application: {e}")
    logger.error(f"Error type: {type(e).__name__}")
    import traceback
    logger.error(f"Traceback: {traceback.format_exc()}")
    raise

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)