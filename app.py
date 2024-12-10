from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from datetime import datetime
from openai import OpenAI
import logging
import json
from secrets_manager import get_service_secrets

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

app = Flask(__name__)
CORS(app)

# Configure API
api = Api(app,
    version='1.0',
    title='Gnosis Metadata API', 
    description='API for extracting and managing content metadata',
    doc='/docs'
)

# Configure namespace
ns = api.namespace('api', description='Metadata operations')

secrets = get_service_secrets('gnosis-metadata')

API_KEY = secrets.get('API_KEY')

C_PORT = int(secrets.get('PORT', 5000))
SQLALCHEMY_DATABASE_URI = (
    f"mysql+pymysql://{secrets['MYSQL_USER']}:{secrets['MYSQL_PASSWORD_CONTENT']}"
    f"@{secrets['MYSQL_HOST']}:{secrets['MYSQL_PORT']}/{secrets['MYSQL_DATABASE']}"
)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

OPENAI_API_KEY = secrets.get('OPENAI_API_KEY')

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

db = SQLAlchemy(app)

class Content(db.Model):
    __tablename__ = 'content'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer, nullable=False)
    s3_key = db.Column(db.String(255))
    chunk_count = db.Column(db.Integer, default=0)
    custom_prompt = db.Column(db.Text)
    # New metadata columns
    title = db.Column(db.String(255))
    author = db.Column(db.String(255))
    publication_date = db.Column(db.Date)
    publisher = db.Column(db.String(255))
    source_language = db.Column(db.String(50))
    genre = db.Column(db.String(100))
    topic = db.Column(db.Text)

def extract_metadata_from_text(text, file_name, additional_info=None):
    """Extract metadata using OpenAI API"""
    context = f"Additional context: {additional_info}\n\n" if additional_info else ""
    
    prompt = f"""
Based on the following text{' and additional context' if additional_info else ''} from the file {file_name}, please extract metadata information.
If you can't determine a specific piece of information with high confidence, use "Unknown".

{context}\n\nText to analyze:
{text[:3000]}  # Using first 3000 characters

Please respond in JSON format with the following structure:
{{
    "title": "Document title",
    "author": "Author name(s)",
    "publication_date": "YYYY-MM-DD or Unknown",
    "publisher": "Publisher name",
    "source_language": "Primary language of the text",
    "genre": "Document genre/category",
    "topic": "Briefly describe the main topic of the document"
}}

Be as specific as possible while maintaining accuracy. For publication_date, 
if only year or year-month is known, use YYYY-01-01 or YYYY-MM-01 format.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a metadata extraction specialist."},
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = response.choices[0].message.content
        response_text = response_text.replace("```json", "").replace("```", "")
        metadata = json.loads(response_text)
        return metadata
        
    except Exception as e:
        logging.error(f"Error extracting metadata: {str(e)}")
        return {
            "title": "Unknown",
            "author": "Unknown",
            "publication_date": "Unknown",
            "publisher": "Unknown",
            "source_language": "Unknown",
            "genre": "Unknown",
            "topic": "Unknown"
        }

# API Models
metadata_request = api.model('MetadataRequest', {
    'text': fields.String(required=True, description='Text to extract metadata from'),
    'file_name': fields.String(description='Name of the file'),
    'additional_info': fields.String(description='Additional context information')
})

metadata_response = api.model('MetadataResponse', {
    'message': fields.String(description='Status message'),
    'metadata': fields.Raw(description='Extracted metadata')
})

content_metadata_response = api.model('ContentMetadataResponse', {
    'message': fields.String(description='Status message'),
    'metadata': fields.Raw(description='Content metadata')
})

@ns.route('/metadata/extract')
class MetadataExtractResource(Resource):
    @api.doc('extract_metadata')
    @api.expect(metadata_request)
    @api.marshal_with(metadata_response)
    def post(self):
        """Extract metadata from provided text"""
        if not request.json or 'text' not in request.json:
            api.abort(400, 'No text provided')
            
        try:
            text = request.json['text']
            file_name = request.json.get('file_name')
            additional_info = request.json.get('additional_info')
            
            metadata = extract_metadata_from_text(text, file_name, additional_info)
            
            return {
                'message': 'Metadata extracted successfully',
                'metadata': metadata
            }, 200
            
        except Exception as e:
            logging.error(f"Error in get_metadata: {str(e)}")
            api.abort(500, 'Internal server error')

@ns.route('/content/<int:content_id>/metadata')
class ContentMetadataResource(Resource):
    @api.doc('get_content_metadata')
    @api.marshal_with(content_metadata_response)
    def get(self, content_id):
        """Get metadata for specific content ID"""
        try:
            content = Content.query.get(content_id)
            
            if not content:
                api.abort(404, 'Content not found')
                
            metadata = {
                'id': content.id,
                'user_id': content.user_id,
                'file_name': content.file_name,
                'file_type': content.file_type,
                'upload_date': content.upload_date.isoformat(),
                'file_size': content.file_size,
                's3_key': content.s3_key,
                'chunk_count': content.chunk_count,
                'title': content.title,
                'author': content.author,
                'publication_date': content.publication_date.isoformat() if content.publication_date else None,
                'publisher': content.publisher,
                'source_language': content.source_language,
                'genre': content.genre,
                'topic': content.topic
            }
            
            return {
                'message': 'Metadata retrieved successfully',
                'metadata': metadata
            }, 200
            
        except Exception as e:
            logging.error(f"Error in get_content_metadata: {str(e)}")
            api.abort(500, 'Internal server error')

@app.before_request
def log_request_info():
    # Exempt the /docs endpoint from logging and API key checks
    if request.path.startswith('/docs') or request.path.startswith('/swagger'):
        return

    logging.info(f"Headers: {request.headers}")
    logging.info(f"Body: {request.get_data()}")

    if 'X-API-KEY' not in request.headers:
        logging.warning("No X-API-KEY header")
        return jsonify({'error': 'No X-API-KEY'}), 401
    
    x_api_key = request.headers.get('X-API-KEY')
    if x_api_key != API_KEY:
        logging.warning("Invalid X-API-KEY")
        return jsonify({'error': 'Invalid X-API-KEY'}), 401
    else:
        return

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=C_PORT)