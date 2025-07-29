from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Collection(db.Model):
    __tablename__ = 'collections'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to photos
    photos = db.relationship('Photo', backref='collection_ref', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'photo_count': len(self.photos)
        }

class Photo(db.Model):
    __tablename__ = 'photos'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    cloudinary_public_id = db.Column(db.String(200), nullable=False, unique=True)
    cloudinary_url = db.Column(db.String(500), nullable=False)
    cloudinary_secure_url = db.Column(db.String(500), nullable=False)
    original_filename = db.Column(db.String(200))
    file_format = db.Column(db.String(10))
    file_size = db.Column(db.Integer)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign key to collection
    collection_id = db.Column(db.Integer, db.ForeignKey('collections.id'), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'cloudinary_public_id': self.cloudinary_public_id,
            'cloudinary_url': self.cloudinary_url,
            'cloudinary_secure_url': self.cloudinary_secure_url,
            'original_filename': self.original_filename,
            'file_format': self.file_format,
            'file_size': self.file_size,
            'width': self.width,
            'height': self.height,
            'uploaded_at': self.uploaded_at.isoformat(),
            'collection_id': self.collection_id,
            'collection_name': self.collection_ref.name if self.collection_ref else None
        }

