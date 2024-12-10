import requests
import logging
from pprint import pprint
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Configuration
# METADATA_SERVICE_URL = 'http://3.85.142.23:80'
METADATA_SERVICE_URL = "http://localhost:5000"
def test_metadata_extraction():
    """Test metadata extraction with various text samples"""
    
    test_cases = [
        {
            "name": "Academic Paper",
            "text": """
            The Theory of Money and Credit
            by Ludwig von Mises
            
            First published in 1912
            
            Introduction
            The tasks of the theory of money and credit can only be adequately outlined if we first understand the basic economic phenomenon of exchange. Exchange is the foundation of all economic activity, and money is its most universal instrument. The understanding of money, therefore, is essential to the understanding of the economic process as a whole.
            """,
            "additional_info": "This is a seminal work in Austrian Economics"
        },
        {
            "name": "Blog Post",
            "text": """
            Why Bitcoin Matters
            By Nick Szabo
            Published on Medium, March 2021
            
            Cryptocurrency has evolved from an academic concept to a full-fledged digital asset class. This article explores the fundamental reasons why Bitcoin and its underlying technology represent a paradigm shift in monetary systems.
            """,
            "additional_info": "Technical blog post about cryptocurrency"
        },
        {
            "name": "Book Chapter",
            "text": """
            Chapter 1: The Nature of Human Action
            
            Human Action: A Treatise on Economics
            By Ludwig von Mises
            Published by Yale University Press, 1949
            
            1. PURPOSEFUL ACTION AND ANIMAL REACTION
            Human action is purposeful behavior. Or we may say: Action is will put into operation and transformed into an agency, is aiming at ends and goals, is the ego's meaningful response to stimuli and to the conditions of its environment, is a person's conscious adjustment to the state of the universe that determines his life.
            """
        }
    ]
    
    for test_case in test_cases:
        logging.info(f"\nTesting metadata extraction for: {test_case['name']}")
        logging.info("-" * 50)
        
        try:
            # Make the extraction request
            response = requests.post(
                f"{METADATA_SERVICE_URL}/api/metadata/extract",
                json={
                    'text': test_case['text'],
                    'additional_info': test_case.get('additional_info')
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logging.info("Extracted Metadata:")
                pprint(result['metadata'])
                
                # Validate metadata fields
                metadata = result['metadata']
                validate_metadata(metadata)
                
            else:
                logging.error(f"Extraction failed with status code: {response.status_code}")
                logging.error(f"Error message: {response.json()}")
                
        except Exception as e:
            logging.error(f"Test failed with error: {str(e)}")

def test_content_metadata_retrieval():
    """Test retrieving metadata for specific content IDs"""
    
    test_content_ids = [1, 2, 3]  # Replace with actual content IDs from your database
    
    for content_id in test_content_ids:
        logging.info(f"\nTesting metadata retrieval for content ID: {content_id}")
        logging.info("-" * 50)
        
        try:
            response = requests.get(
                f"{METADATA_SERVICE_URL}/api/content/{content_id}/metadata"
            )
            
            if response.status_code == 200:
                result = response.json()
                logging.info("Retrieved Metadata:")
                pprint(result['metadata'])
                
            elif response.status_code == 404:
                logging.warning(f"Content ID {content_id} not found")
            else:
                logging.error(f"Retrieval failed with status code: {response.status_code}")
                logging.error(f"Error message: {response.json()}")
                
        except Exception as e:
            logging.error(f"Test failed with error: {str(e)}")

def validate_metadata(metadata):
    """Validate metadata fields"""
    required_fields = [
        'title', 'author', 'publication_date', 
        'publisher', 'source_language', 'genre'
    ]
    
    for field in required_fields:
        if field not in metadata:
            logging.warning(f"Missing field in metadata: {field}")
        elif metadata[field] == "Unknown":
            logging.info(f"Field {field} is Unknown")
        else:
            logging.info(f"Field {field}: {metadata[field]}")
    
    # Validate date format if not Unknown
    if metadata['publication_date'] != "Unknown":
        try:
            datetime.strptime(metadata['publication_date'], '%Y-%m-%d')
            logging.info("Publication date format is valid")
        except ValueError:
            logging.warning("Invalid publication date format")

def run_tests():
    """Run all tests"""
    logging.info("Starting metadata service tests...")
    
    logging.info("\n=== Testing Metadata Extraction ===")
    test_metadata_extraction()
    
    logging.info("\n=== Testing Content Metadata Retrieval ===")
    test_content_metadata_retrieval()
    
    logging.info("\nTests completed!")

if __name__ == "__main__":
    run_tests()