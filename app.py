import os
import sys
import json
import time
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.utils import cloudinary_url
import requests
from functools import wraps

app = Flask(__name__, static_folder='static')
CORS(app)

# Configure Cloudinary with error handling
try:
    cloudinary.config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET')
    )
    print("✅ Cloudinary configured successfully")
except Exception as e:
    print(f"❌ Cloudinary configuration failed: {e}")

# Global error handler decorator
def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            print(f"❌ Error in {f.__name__}: {e}")
            print(f"📍 Traceback: {traceback.format_exc()}")
            return jsonify({'error': str(e), 'success': False}), 500
    return decorated_function

# Retry decorator for Cloudinary operations
def retry_cloudinary(max_retries=3, delay=1):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    print(f"⚠️ Cloudinary operation failed (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
                    else:
                        raise e
            return None
        return wrapper
    return decorator

# Safe file operations
def safe_read_json(filepath, default=None):
    """Safely read JSON file with error handling"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
                print(f"📁 Loaded data from {filepath}")
                return data
        else:
            print(f"📄 File {filepath} doesn't exist, using default")
            return default if default is not None else []
    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
        return default if default is not None else []

def safe_write_json(filepath, data):
    """Safely write JSON file with error handling"""
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"💾 Saved data to {filepath}")
        return True
    except Exception as e:
        print(f"❌ Error writing {filepath}: {e}")
        return False

# Collections management with error handling
COLLECTIONS_FILE = 'collections_data.json'

def load_collections_data():
    """Load collections with comprehensive error handling"""
    try:
        collections = safe_read_json(COLLECTIONS_FILE, [])
        print(f"📁 Loaded {len(collections)} collections from local cache")
        return collections
    except Exception as e:
        print(f"❌ Error loading collections: {e}")
        return []

def save_collections_data(collections):
    """Save collections with error handling"""
    try:
        success = safe_write_json(COLLECTIONS_FILE, collections)
        if success:
            print(f"💾 Saved {len(collections)} collections to local cache")
        return success
    except Exception as e:
        print(f"❌ Error saving collections: {e}")
        return False

@retry_cloudinary(max_retries=3)
def load_photos_from_cloudinary():
    """Load photos from Cloudinary with retry logic"""
    print("☁️ Loading photos from Cloudinary...")
    
    try:
        # Get all resources from Cloudinary
        result = cloudinary.api.resources(
            resource_type="image",
            max_results=500,
            context=True
        )
        
        photos = []
        for resource in result.get('resources', []):
            try:
                # Extract metadata safely
                context = resource.get('context', {}).get('custom', {}) if resource.get('context') else {}
                
                photo = {
                    'id': len(photos),
                    'public_id': resource.get('public_id', ''),
                    'title': context.get('title', resource.get('public_id', 'Untitled')),
                    'description': context.get('description', ''),
                    'url': resource.get('secure_url', ''),
                    'collection_id': context.get('collection_id', None),
                    'collection_name': context.get('collection_name', None),
                    'created_at': resource.get('created_at', '')
                }
                photos.append(photo)
            except Exception as e:
                print(f"⚠️ Error processing photo {resource.get('public_id', 'unknown')}: {e}")
                continue
        
        print(f"✅ Loaded {len(photos)} photos from Cloudinary")
        return photos
        
    except Exception as e:
        print(f"❌ Failed to load photos from Cloudinary: {e}")
        return []

# API Routes with comprehensive error handling

@app.route('/')
def index():
    """Serve the main page"""
    try:
        return send_from_directory('static', 'index.html')
    except Exception as e:
        print(f"❌ Error serving index: {e}")
        return f"Error loading page: {e}", 500

@app.route('/api/photos')
@handle_errors
def get_photos():
    """Get all photos with error handling"""
    photos = load_photos_from_cloudinary()
    return jsonify(photos)

@app.route('/api/collections')
@handle_errors
def get_collections():
    """Get all collections with error handling"""
    collections = load_collections_data()
    return jsonify(collections)

@app.route('/api/collections', methods=['POST'])
@handle_errors
def create_collection():
    """Create a new collection with error handling"""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'error': 'Collection name is required', 'success': False}), 400
        
        name = data['name'].strip()
        if not name:
            return jsonify({'error': 'Collection name cannot be empty', 'success': False}), 400
        
        # Load existing collections
        collections = load_collections_data()
        
        # Check for duplicate names
        for collection in collections:
            if collection.get('name', '').lower() == name.lower():
                return jsonify({'error': 'Collection name already exists', 'success': False}), 400
        
        # Generate stable ID based on name
        import hashlib
        stable_id = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
        
        # Create new collection
        new_collection = {
            'id': stable_id,
            'name': name,
            'created_at': datetime.now().isoformat(),
            'photo_count': 0
        }
        
        collections.append(new_collection)
        
        # Save to local file
        if save_collections_data(collections):
            print(f"📁 Created collection: {name} (ID: {stable_id})")
            return jsonify({'message': f'Collection "{name}" created successfully', 'collection': new_collection, 'success': True})
        else:
            return jsonify({'error': 'Failed to save collection', 'success': False}), 500
            
    except Exception as e:
        print(f"❌ Error creating collection: {e}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/collections/<int:collection_id>', methods=['DELETE'])
@handle_errors
def delete_collection(collection_id):
    """Delete a collection with error handling"""
    try:
        collections = load_collections_data()
        
        # Find and remove the collection
        collection_to_delete = None
        for i, collection in enumerate(collections):
            if collection.get('id') == collection_id:
                collection_to_delete = collections.pop(i)
                break
        
        if not collection_to_delete:
            return jsonify({'error': 'Collection not found', 'success': False}), 404
        
        # Save updated collections
        if save_collections_data(collections):
            print(f"🗑️ Deleted collection: {collection_to_delete.get('name', 'Unknown')}")
            return jsonify({'message': 'Collection deleted successfully', 'success': True})
        else:
            return jsonify({'error': 'Failed to save changes', 'success': False}), 500
            
    except Exception as e:
        print(f"❌ Error deleting collection: {e}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/photos/<int:photo_id>/collection', methods=['PUT'])
@handle_errors
def update_photo_collection(photo_id):
    """Update photo collection assignment with error handling"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required', 'success': False}), 400
        
        collection_id = data.get('collection_id')
        collection_name = data.get('collection_name', '')
        
        # Load photos to find the target photo
        photos = load_photos_from_cloudinary()
        
        if photo_id >= len(photos):
            return jsonify({'error': 'Photo not found', 'success': False}), 404
        
        photo = photos[photo_id]
        public_id = photo.get('public_id')
        
        if not public_id:
            return jsonify({'error': 'Photo public_id not found', 'success': False}), 400
        
        # Update photo context in Cloudinary
        context_data = {
            'title': photo.get('title', ''),
            'description': photo.get('description', ''),
            'collection_id': str(collection_id) if collection_id else '',
            'collection_name': collection_name
        }
        
        # Remove empty values
        context_data = {k: v for k, v in context_data.items() if v}
        
        try:
            cloudinary.uploader.add_context(context_data, public_id)
            print(f"✅ Updated photo collection in Cloudinary: {photo.get('title', 'Untitled')}")
            return jsonify({'message': 'Photo collection updated successfully', 'success': True})
        except Exception as cloudinary_error:
            print(f"❌ Cloudinary update failed: {cloudinary_error}")
            return jsonify({'error': f'Failed to update photo in Cloudinary: {cloudinary_error}', 'success': False}), 500
            
    except Exception as e:
        print(f"❌ Error updating photo collection: {e}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/photos', methods=['POST'])
@handle_errors
def upload_photo():
    """Upload photo with comprehensive error handling"""
    try:
        if 'photos' not in request.files:
            return jsonify({'error': 'No photos provided', 'success': False}), 400
        
        files = request.files.getlist('photos')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'error': 'No photos selected', 'success': False}), 400
        
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        collection_id = request.form.get('collection_id', '').strip()
        collection_name = request.form.get('collection_name', '').strip()
        
        uploaded_photos = []
        
        for file in files:
            if file and file.filename:
                try:
                    # Prepare context data
                    context_data = {}
                    if title:
                        context_data['title'] = title
                    if description:
                        context_data['description'] = description
                    if collection_id and collection_id != '0':
                        context_data['collection_id'] = collection_id
                    if collection_name:
                        context_data['collection_name'] = collection_name
                    
                    # Upload to Cloudinary
                    upload_result = cloudinary.uploader.upload(
                        file,
                        context=context_data,
                        resource_type="auto"
                    )
                    
                    uploaded_photos.append({
                        'public_id': upload_result.get('public_id'),
                        'url': upload_result.get('secure_url'),
                        'title': title or file.filename
                    })
                    
                    print(f"📸 Uploaded photo: {title or file.filename}")
                    
                except Exception as upload_error:
                    print(f"❌ Failed to upload {file.filename}: {upload_error}")
                    continue
        
        if uploaded_photos:
            return jsonify({
                'message': f'Successfully uploaded {len(uploaded_photos)} photo(s)',
                'photos': uploaded_photos,
                'success': True
            })
        else:
            return jsonify({'error': 'Failed to upload any photos', 'success': False}), 500
            
    except Exception as e:
        print(f"❌ Error in photo upload: {e}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/photos/<int:photo_id>', methods=['DELETE'])
@handle_errors
def delete_photo(photo_id):
    """Delete photo with error handling"""
    try:
        photos = load_photos_from_cloudinary()
        
        if photo_id >= len(photos):
            return jsonify({'error': 'Photo not found', 'success': False}), 404
        
        photo = photos[photo_id]
        public_id = photo.get('public_id')
        
        if not public_id:
            return jsonify({'error': 'Photo public_id not found', 'success': False}), 400
        
        try:
            # Delete from Cloudinary
            cloudinary.uploader.destroy(public_id)
            print(f"✅ Deleted from Cloudinary: {photo.get('title', 'Untitled')}")
            print(f"🗑️ Deleted photo: {photo.get('title', 'Untitled')}")
            return jsonify({'message': 'Photo deleted successfully', 'success': True})
        except Exception as cloudinary_error:
            print(f"❌ Cloudinary deletion failed: {cloudinary_error}")
            return jsonify({'error': f'Failed to delete from Cloudinary: {cloudinary_error}', 'success': False}), 500
            
    except Exception as e:
        print(f"❌ Error deleting photo: {e}")
        return jsonify({'error': str(e), 'success': False}), 500

# Health check endpoint
@app.route('/api/health')
@handle_errors
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'cloudinary_configured': bool(os.getenv('CLOUDINARY_CLOUD_NAME')),
        'success': True
    })

# Global error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found', 'success': False}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'success': False}), 500

if __name__ == '__main__':
    print("🚀 Starting George's Photo Gallery (STABLE VERSION)")
    print("🛡️ Enhanced error handling and stability features enabled")
    app.run(host='0.0.0.0', port=5006, debug=False)

