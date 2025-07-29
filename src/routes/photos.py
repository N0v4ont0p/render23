import os
import cloudinary
import cloudinary.uploader
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from src.models.photo import db, Photo, Collection
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

photos_bp = Blueprint('photos', __name__)

@photos_bp.route('/photos', methods=['GET'])
def get_photos():
    """Get all photos with optional collection filtering"""
    try:
        collection_id = request.args.get('collection_id')
        
        if collection_id:
            photos = Photo.query.filter_by(collection_id=collection_id).order_by(Photo.uploaded_at.desc()).all()
        else:
            photos = Photo.query.order_by(Photo.uploaded_at.desc()).all()
        
        return jsonify({
            'success': True,
            'photos': [photo.to_dict() for photo in photos]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@photos_bp.route('/photos', methods=['POST'])
def upload_photos():
    """Upload multiple photos to Cloudinary and save metadata to database"""
    try:
        # Check if files are present
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No files provided'
            }), 400
        
        files = request.files.getlist('files')
        if not files or all(file.filename == '' for file in files):
            return jsonify({
                'success': False,
                'error': 'No files selected'
            }), 400
        
        # Get form data
        titles = request.form.getlist('titles')
        descriptions = request.form.getlist('descriptions')
        collection_id = request.form.get('collection_id')
        
        # Validate collection if provided
        collection = None
        if collection_id and collection_id != '':
            collection = Collection.query.get(collection_id)
            if not collection:
                return jsonify({
                    'success': False,
                    'error': 'Collection not found'
                }), 404
        
        uploaded_photos = []
        
        for i, file in enumerate(files):
            if file and file.filename:
                try:
                    # Get metadata for this photo
                    title = titles[i] if i < len(titles) and titles[i] else secure_filename(file.filename)
                    description = descriptions[i] if i < len(descriptions) and descriptions[i] else ''
                    
                    # Upload to Cloudinary
                    upload_result = cloudinary.uploader.upload(
                        file,
                        folder="photo_gallery",
                        resource_type="image",
                        quality="auto",
                        fetch_format="auto"
                    )
                    
                    # Create photo record in database
                    photo = Photo(
                        title=title,
                        description=description,
                        cloudinary_public_id=upload_result['public_id'],
                        cloudinary_url=upload_result['url'],
                        cloudinary_secure_url=upload_result['secure_url'],
                        original_filename=file.filename,
                        file_format=upload_result.get('format'),
                        file_size=upload_result.get('bytes'),
                        width=upload_result.get('width'),
                        height=upload_result.get('height'),
                        collection_id=collection.id if collection else None
                    )
                    
                    db.session.add(photo)
                    uploaded_photos.append(photo)
                    
                except Exception as e:
                    current_app.logger.error(f"Error uploading file {file.filename}: {str(e)}")
                    continue
        
        # Commit all photos to database
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully uploaded {len(uploaded_photos)} photos',
            'photos': [photo.to_dict() for photo in uploaded_photos]
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in upload_photos: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@photos_bp.route('/photos/<int:photo_id>', methods=['DELETE'])
def delete_photo(photo_id):
    """Delete a photo from both Cloudinary and database"""
    try:
        photo = Photo.query.get(photo_id)
        if not photo:
            return jsonify({
                'success': False,
                'error': 'Photo not found'
            }), 404
        
        # Delete from Cloudinary
        try:
            cloudinary.uploader.destroy(photo.cloudinary_public_id)
        except Exception as e:
            current_app.logger.warning(f"Failed to delete from Cloudinary: {str(e)}")
        
        # Delete from database
        db.session.delete(photo)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Photo deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@photos_bp.route('/photos/<int:photo_id>/collection', methods=['PUT'])
def update_photo_collection(photo_id):
    """Update the collection assignment for a photo"""
    try:
        photo = Photo.query.get(photo_id)
        if not photo:
            return jsonify({
                'success': False,
                'error': 'Photo not found'
            }), 404
        
        data = request.get_json()
        collection_id = data.get('collection_id')
        
        # Validate collection if provided
        if collection_id and collection_id != '':
            collection = Collection.query.get(collection_id)
            if not collection:
                return jsonify({
                    'success': False,
                    'error': 'Collection not found'
                }), 404
            photo.collection_id = collection_id
        else:
            photo.collection_id = None
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Photo collection updated successfully',
            'photo': photo.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@photos_bp.route('/photos/bulk-update', methods=['PUT'])
def bulk_update_photos():
    """Bulk update collection assignment for multiple photos"""
    try:
        data = request.get_json()
        photo_ids = data.get('photo_ids', [])
        collection_id = data.get('collection_id')
        
        if not photo_ids:
            return jsonify({
                'success': False,
                'error': 'No photo IDs provided'
            }), 400
        
        # Validate collection if provided
        collection = None
        if collection_id and collection_id != '':
            collection = Collection.query.get(collection_id)
            if not collection:
                return jsonify({
                    'success': False,
                    'error': 'Collection not found'
                }), 404
        
        # Update photos
        photos = Photo.query.filter(Photo.id.in_(photo_ids)).all()
        for photo in photos:
            photo.collection_id = collection.id if collection else None
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully updated {len(photos)} photos',
            'updated_count': len(photos)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@photos_bp.route('/photos/bulk-delete', methods=['DELETE'])
def bulk_delete_photos():
    """Bulk delete multiple photos"""
    try:
        data = request.get_json()
        photo_ids = data.get('photo_ids', [])
        
        if not photo_ids:
            return jsonify({
                'success': False,
                'error': 'No photo IDs provided'
            }), 400
        
        photos = Photo.query.filter(Photo.id.in_(photo_ids)).all()
        
        # Delete from Cloudinary
        for photo in photos:
            try:
                cloudinary.uploader.destroy(photo.cloudinary_public_id)
            except Exception as e:
                current_app.logger.warning(f"Failed to delete {photo.cloudinary_public_id} from Cloudinary: {str(e)}")
        
        # Delete from database
        for photo in photos:
            db.session.delete(photo)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {len(photos)} photos',
            'deleted_count': len(photos)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

