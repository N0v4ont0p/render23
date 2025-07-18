import os
import sys
import json
import time
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import cloudinary
import cloudinary.uploader
import cloudinary.api

app = Flask(__name__, static_folder='static')
CORS(app, origins="*")

# Configure Cloudinary
try:
    cloudinary.config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET')
    )
    print("✅ Cloudinary configured successfully")
except Exception as e:
    print(f"❌ Cloudinary configuration failed: {e}")

# Collections are now stored as special metadata in Cloudinary
# We use a special "collections_registry" resource to store collection data
COLLECTIONS_REGISTRY_ID = "photo_gallery_collections_registry"

def get_collections_from_cloudinary():
    """Load collections data from Cloudinary metadata"""
    try:
        print("☁️ Loading collections from Cloudinary...")
        
        # Try to get the collections registry resource
        try:
            result = cloudinary.api.resource(COLLECTIONS_REGISTRY_ID, resource_type="raw")
            collections_url = result.get('secure_url')
            
            # Download the collections data
            import requests
            response = requests.get(collections_url)
            if response.status_code == 200:
                collections_data = response.json()
                print(f"✅ Loaded {len(collections_data)} collections from Cloudinary")
                return collections_data
            else:
                print("📄 Collections registry not found, using empty list")
                return []
        except cloudinary.exceptions.NotFound:
            print("📄 Collections registry not found, using empty list")
            return []
        except Exception as e:
            print(f"⚠️ Error loading collections from Cloudinary: {e}")
            return []
            
    except Exception as e:
        print(f"❌ Error accessing Cloudinary: {e}")
        return []

def save_collections_to_cloudinary(collections):
    """Save collections data to Cloudinary"""
    try:
        print("☁️ Saving collections to Cloudinary...")
        
        # Create a temporary file with collections data
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(collections, f, indent=2)
            temp_file = f.name
        
        # Upload to Cloudinary as raw file
        result = cloudinary.uploader.upload(
            temp_file,
            public_id=COLLECTIONS_REGISTRY_ID,
            resource_type="raw",
            overwrite=True
        )
        
        # Clean up temp file
        os.unlink(temp_file)
        
        print(f"✅ Collections saved to Cloudinary: {result.get('secure_url')}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving collections to Cloudinary: {e}")
        return False

def get_photos_from_cloudinary():
    """Load all photos from Cloudinary with their metadata"""
    try:
        print("☁️ Loading photos from Cloudinary...")
        
        # Get all images from Cloudinary
        result = cloudinary.api.resources(
            resource_type="image",
            max_results=500,
            context=True
        )
        
        photos = []
        for resource in result.get('resources', []):
            photo = {
                'id': resource.get('public_id'),
                'url': resource.get('secure_url'),
                'title': resource.get('context', {}).get('title', resource.get('public_id')),
                'description': resource.get('context', {}).get('description', ''),
                'collection_id': resource.get('context', {}).get('collection_id', ''),
                'collection_name': resource.get('context', {}).get('collection_name', ''),
                'created_at': resource.get('created_at', ''),
                'width': resource.get('width', 0),
                'height': resource.get('height', 0),
                'format': resource.get('format', ''),
                'bytes': resource.get('bytes', 0)
            }
            photos.append(photo)
        
        print(f"✅ Loaded {len(photos)} photos from Cloudinary")
        return photos
        
    except Exception as e:
        print(f"❌ Error loading photos from Cloudinary: {e}")
        return []

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'cloudinary_configured': bool(os.getenv('CLOUDINARY_CLOUD_NAME')),
        'success': True
    })

@app.route('/api/photos', methods=['GET'])
def get_photos():
    try:
        photos = get_photos_from_cloudinary()
        return jsonify(photos)
    except Exception as e:
        print(f"❌ Error in get_photos: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to load photos: {str(e)}'
        }), 500

@app.route('/api/collections', methods=['GET'])
def get_collections():
    try:
        collections = get_collections_from_cloudinary()
        photos = get_photos_from_cloudinary()
        
        # Calculate photo counts for each collection
        for collection in collections:
            collection['photo_count'] = len([p for p in photos if p.get('collection_id') == str(collection['id'])])
        
        return jsonify(collections)
    except Exception as e:
        print(f"❌ Error in get_collections: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to load collections: {str(e)}'
        }), 500

@app.route('/api/collections', methods=['POST'])
def create_collection():
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({
                'success': False,
                'error': 'Collection name is required'
            }), 400
        
        # Load existing collections
        collections = get_collections_from_cloudinary()
        
        # Check if collection already exists
        if any(c['name'].lower() == name.lower() for c in collections):
            return jsonify({
                'success': False,
                'error': 'Collection with this name already exists'
            }), 400
        
        # Create new collection
        new_collection = {
            'id': len(collections) + 1,
            'name': name,
            'created_at': datetime.now().isoformat(),
            'photo_count': 0
        }
        
        collections.append(new_collection)
        
        # Save to Cloudinary
        if save_collections_to_cloudinary(collections):
            return jsonify({
                'success': True,
                'message': f'Collection "{name}" created successfully!',
                'collection': new_collection
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save collection to storage'
            }), 500
            
    except Exception as e:
        print(f"❌ Error creating collection: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to create collection: {str(e)}'
        }), 500

@app.route('/api/collections/<int:collection_id>', methods=['DELETE'])
def delete_collection(collection_id):
    try:
        # Load existing collections
        collections = get_collections_from_cloudinary()
        
        # Find and remove the collection
        collection_to_delete = None
        for i, collection in enumerate(collections):
            if collection['id'] == collection_id:
                collection_to_delete = collections.pop(i)
                break
        
        if not collection_to_delete:
            return jsonify({
                'success': False,
                'error': 'Collection not found'
            }), 404
        
        # Remove collection assignment from all photos
        photos = get_photos_from_cloudinary()
        for photo in photos:
            if photo.get('collection_id') == str(collection_id):
                try:
                    # Update photo context to remove collection
                    context_data = {
                        'title': photo.get('title', ''),
                        'description': photo.get('description', ''),
                    }
                    
                    # Remove empty values
                    context_data = {k: v for k, v in context_data.items() if v}
                    
                    cloudinary.uploader.add_context(
                        context_data,
                        public_ids=[photo['id']]
                    )
                    print(f"✅ Removed collection from photo: {photo['id']}")
                except Exception as e:
                    print(f"⚠️ Error removing collection from photo {photo['id']}: {e}")
        
        # Save updated collections to Cloudinary
        if save_collections_to_cloudinary(collections):
            return jsonify({
                'success': True,
                'message': f'Collection "{collection_to_delete["name"]}" deleted successfully!'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save changes to storage'
            }), 500
            
    except Exception as e:
        print(f"❌ Error deleting collection: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to delete collection: {str(e)}'
        }), 500

@app.route('/api/photos', methods=['POST'])
def upload_photos():
    try:
        if 'photos' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No photos provided'
            }), 400
        
        files = request.files.getlist('photos')
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        collection_id = request.form.get('collection_id', '').strip()
        collection_name = request.form.get('collection_name', '').strip()
        
        uploaded_photos = []
        
        for file in files:
            if file and file.filename:
                try:
                    # Generate unique public_id
                    public_id = f"photo_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                    
                    # Prepare context data
                    context_data = {
                        'title': title or file.filename,
                        'description': description,
                    }
                    
                    # Add collection info if provided
                    if collection_id and collection_name:
                        context_data['collection_id'] = str(collection_id)
                        context_data['collection_name'] = collection_name
                    
                    # Remove empty values
                    context_data = {k: v for k, v in context_data.items() if v}
                    
                    # Upload to Cloudinary
                    result = cloudinary.uploader.upload(
                        file,
                        public_id=public_id,
                        context=context_data,
                        resource_type="image"
                    )
                    
                    uploaded_photos.append({
                        'id': result['public_id'],
                        'url': result['secure_url'],
                        'title': context_data.get('title', ''),
                        'description': context_data.get('description', ''),
                        'collection_id': context_data.get('collection_id', ''),
                        'collection_name': context_data.get('collection_name', '')
                    })
                    
                    print(f"✅ Uploaded photo: {result['public_id']}")
                    
                except Exception as e:
                    print(f"❌ Error uploading {file.filename}: {e}")
                    continue
        
        if uploaded_photos:
            return jsonify({
                'success': True,
                'message': f'Successfully uploaded {len(uploaded_photos)} photo(s)!',
                'photos': uploaded_photos
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No photos were uploaded successfully'
            }), 500
            
    except Exception as e:
        print(f"❌ Error in upload_photos: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to upload photos: {str(e)}'
        }), 500

@app.route('/api/photos/<photo_id>', methods=['DELETE'])
def delete_photo(photo_id):
    try:
        # Delete from Cloudinary
        result = cloudinary.uploader.destroy(photo_id)
        
        if result.get('result') == 'ok':
            return jsonify({
                'success': True,
                'message': 'Photo deleted successfully!'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete photo from storage'
            }), 500
            
    except Exception as e:
        print(f"❌ Error deleting photo: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to delete photo: {str(e)}'
        }), 500

@app.route('/api/photos/<photo_id>/collection', methods=['PUT'])
def update_photo_collection(photo_id):
    try:
        data = request.get_json()
        collection_id = data.get('collection_id')
        collection_name = data.get('collection_name', '')
        
        # Get current photo info
        try:
            photo_info = cloudinary.api.resource(photo_id, context=True)
            current_context = photo_info.get('context', {})
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Photo not found'
            }), 404
        
        # Prepare new context data
        context_data = {
            'title': current_context.get('title', ''),
            'description': current_context.get('description', ''),
        }
        
        # Add collection info if provided, or remove if empty
        if collection_id and collection_name:
            context_data['collection_id'] = str(collection_id)
            context_data['collection_name'] = collection_name
        elif collection_id == '' or collection_id is None:
            # Remove collection assignment - don't add collection fields to context
            pass
        
        # Remove empty values
        context_data = {k: v for k, v in context_data.items() if v}
        
        # Update context in Cloudinary
        cloudinary.uploader.add_context(
            context_data,
            public_ids=[photo_id]
        )
        
        action = "removed from collection" if not collection_id else f"added to collection '{collection_name}'"
        
        return jsonify({
            'success': True,
            'message': f'Photo {action} successfully!'
        })
        
    except Exception as e:
        print(f"❌ Error updating photo collection: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to update photo collection: {str(e)}'
        }), 500

@app.route('/api/photos/bulk-update', methods=['PUT'])
def bulk_update_photos():
    try:
        data = request.get_json()
        photo_ids = data.get('photo_ids', [])
        collection_id = data.get('collection_id')
        collection_name = data.get('collection_name', '')
        
        if not photo_ids:
            return jsonify({
                'success': False,
                'error': 'No photos selected'
            }), 400
        
        updated_count = 0
        
        for photo_index in photo_ids:
            try:
                # Get all photos to find the actual photo ID
                photos = get_photos_from_cloudinary()
                if photo_index >= len(photos):
                    continue
                    
                photo = photos[photo_index]
                photo_id = photo['id']
                
                # Prepare context data
                context_data = {
                    'title': photo.get('title', ''),
                    'description': photo.get('description', ''),
                }
                
                # Add collection info if provided, or remove if empty
                if collection_id and collection_name:
                    context_data['collection_id'] = str(collection_id)
                    context_data['collection_name'] = collection_name
                elif collection_id == '' or collection_id is None:
                    # Remove collection assignment - don't add collection fields to context
                    pass
                
                # Remove empty values
                context_data = {k: v for k, v in context_data.items() if v}
                
                # Update context in Cloudinary
                cloudinary.uploader.add_context(
                    context_data,
                    public_ids=[photo_id]
                )
                
                updated_count += 1
                print(f"✅ Updated photo: {photo_id}")
                
            except Exception as e:
                print(f"❌ Error updating photo {photo_index}: {e}")
                continue
        
        action = "removed from collection" if not collection_id else f"added to collection '{collection_name}'"
        
        return jsonify({
            'success': True,
            'message': f'Successfully {action} for {updated_count} photo(s)!'
        })
        
    except Exception as e:
        print(f"❌ Error in bulk_update_photos: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to update photos: {str(e)}'
        }), 500

@app.route('/api/photos/bulk-delete', methods=['DELETE'])
def bulk_delete_photos():
    try:
        data = request.get_json()
        photo_ids = data.get('photo_ids', [])
        
        if not photo_ids:
            return jsonify({
                'success': False,
                'error': 'No photos selected'
            }), 400
        
        # Get all photos to find the actual photo IDs
        photos = get_photos_from_cloudinary()
        
        deleted_count = 0
        
        for photo_index in photo_ids:
            try:
                if photo_index >= len(photos):
                    continue
                    
                photo = photos[photo_index]
                photo_id = photo['id']
                
                # Delete from Cloudinary
                result = cloudinary.uploader.destroy(photo_id)
                
                if result.get('result') == 'ok':
                    deleted_count += 1
                    print(f"✅ Deleted photo: {photo_id}")
                else:
                    print(f"⚠️ Failed to delete photo: {photo_id}")
                    
            except Exception as e:
                print(f"❌ Error deleting photo {photo_index}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {deleted_count} photo(s)!'
        })
        
    except Exception as e:
        print(f"❌ Error in bulk_delete_photos: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to delete photos: {str(e)}'
        }), 500

@app.route('/api/collections/<int:collection_id>/photos')
def get_collection_photos(collection_id):
    try:
        photos = get_photos_from_cloudinary()
        collection_photos = [p for p in photos if p.get('collection_id') == str(collection_id)]
        
        print(f"📁 Found {len(collection_photos)} photos in collection {collection_id}")
        
        return jsonify(collection_photos)
        
    except Exception as e:
        print(f"❌ Error getting collection photos: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to load collection photos: {str(e)}'
        }), 500

if __name__ == '__main__':
    print("🚀 Starting George's Photo Gallery (PERSISTENT VERSION)")
    print("🛡️ Enhanced error handling and stability features enabled")
    print("✨ New features: Accurate photo counts, tag cleanup, mass delete, photo preview")
    print("💾 PERSISTENT COLLECTIONS: Collections now stored in Cloudinary!")
    app.run(host='0.0.0.0', port=5010, debug=False)

