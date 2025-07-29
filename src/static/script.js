// Photo Gallery JavaScript
class PhotoGallery {
    constructor() {
        this.currentView = 'gallery';
        this.currentCollection = null;
        this.selectedPhotos = new Set();
        this.isLoggedIn = false;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.checkAuthStatus();
        this.loadCollections();
        this.loadPhotos();
    }
    
    bindEvents() {
        // Navigation
        document.getElementById('adminBtn').addEventListener('click', () => this.showView('admin'));
        document.getElementById('homeBtn').addEventListener('click', () => this.showView('gallery'));
        document.getElementById('backToGallery').addEventListener('click', () => this.showAllPhotos());
        
        // Admin login
        document.getElementById('loginForm').addEventListener('submit', (e) => this.handleLogin(e));
        
        // Upload functionality
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        
        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        uploadArea.addEventListener('drop', (e) => this.handleDrop(e));
        fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        document.getElementById('uploadBtn').addEventListener('click', () => this.uploadPhotos());
        
        // Collection management
        document.getElementById('addCollectionBtn').addEventListener('click', () => this.addCollection());
        document.getElementById('newCollectionName').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.addCollection();
        });
        
        // Bulk operations
        document.getElementById('selectAllPhotos').addEventListener('change', (e) => this.toggleSelectAll(e));
        document.getElementById('bulkAssignBtn').addEventListener('click', () => this.bulkAssignCollection());
        document.getElementById('bulkDeleteBtn').addEventListener('click', () => this.bulkDeletePhotos());
        
        // Modal
        document.getElementById('closeModal').addEventListener('click', () => this.closeModal());
        document.getElementById('photoModal').addEventListener('click', (e) => {
            if (e.target.id === 'photoModal' || e.target.classList.contains('modal-backdrop')) {
                this.closeModal();
            }
        });
        document.getElementById('downloadBtn').addEventListener('click', () => this.downloadPhoto());
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.closeModal();
        });
    }
    
    async checkAuthStatus() {
        try {
            const response = await fetch('/api/auth/status');
            const data = await response.json();
            this.isLoggedIn = data.logged_in;
            
            if (this.isLoggedIn) {
                this.showAdminPanel();
                this.loadAdminData();
            }
        } catch (error) {
            console.error('Error checking auth status:', error);
        }
    }
    
    showView(view) {
        // Update navigation
        document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
        document.getElementById(view === 'admin' ? 'adminBtn' : 'homeBtn').classList.add('active');
        
        // Update views
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.getElementById(view === 'admin' ? 'adminView' : 'galleryView').classList.add('active');
        
        this.currentView = view;
    }
    
    async handleLogin(e) {
        e.preventDefault();
        const password = document.getElementById('adminPassword').value;
        
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.isLoggedIn = true;
                this.showAdminPanel();
                this.loadAdminData();
                this.showToast('Login successful', 'success');
            } else {
                this.showToast(data.error || 'Login failed', 'error');
            }
        } catch (error) {
            this.showToast('Login error: ' + error.message, 'error');
        }
    }
    
    showAdminPanel() {
        document.getElementById('adminLogin').style.display = 'none';
        document.getElementById('adminPanel').style.display = 'block';
    }
    
    async loadCollections() {
        try {
            const response = await fetch('/api/collections');
            const data = await response.json();
            
            if (data.success) {
                this.renderCollections(data.collections);
            } else {
                this.showEmptyState('collectionsGrid', 'No collections created yet', 'Create your first collection in the admin panel');
            }
        } catch (error) {
            console.error('Error loading collections:', error);
            this.showEmptyState('collectionsGrid', 'Error loading collections', 'Please try refreshing the page');
        }
    }
    
    async loadPhotos(collectionId = null) {
        try {
            const url = collectionId ? `/api/photos?collection_id=${collectionId}` : '/api/photos';
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.success) {
                this.renderPhotos(data.photos);
                this.updatePhotosTitle(collectionId);
            } else {
                this.showEmptyState('photosGrid', 'No photos uploaded yet', 'Upload your first photos in the admin panel');
            }
        } catch (error) {
            console.error('Error loading photos:', error);
            this.showEmptyState('photosGrid', 'Error loading photos', 'Please try refreshing the page');
        }
    }
    
    renderCollections(collections) {
        const grid = document.getElementById('collectionsGrid');
        
        if (collections.length === 0) {
            this.showEmptyState('collectionsGrid', 'No collections created yet', 'Create your first collection in the admin panel');
            return;
        }
        
        grid.innerHTML = collections.map(collection => `
            <div class="collection-card" onclick="photoGallery.showCollection(${collection.id}, '${collection.name}')">
                <h3>${this.escapeHtml(collection.name)}</h3>
                <p>${collection.photo_count} photo${collection.photo_count !== 1 ? 's' : ''}</p>
            </div>
        `).join('');
    }
    
    renderPhotos(photos) {
        const grid = document.getElementById('photosGrid');
        
        if (photos.length === 0) {
            this.showEmptyState('photosGrid', 'No photos in this collection', 'Add photos to this collection in the admin panel');
            return;
        }
        
        grid.innerHTML = photos.map(photo => `
            <div class="photo-card" onclick="photoGallery.showPhotoModal(${photo.id})">
                <img src="${photo.cloudinary_secure_url}" alt="${this.escapeHtml(photo.title)}" loading="lazy">
                <div class="photo-card-content">
                    <h3>${this.escapeHtml(photo.title)}</h3>
                    <p>${this.escapeHtml(photo.description || '')}</p>
                </div>
            </div>
        `).join('');
    }
    
    showCollection(collectionId, collectionName) {
        this.currentCollection = { id: collectionId, name: collectionName };
        this.loadPhotos(collectionId);
        document.getElementById('backToGallery').style.display = 'inline-flex';
    }
    
    showAllPhotos() {
        this.currentCollection = null;
        this.loadPhotos();
        this.updatePhotosTitle();
        document.getElementById('backToGallery').style.display = 'none';
    }
    
    updatePhotosTitle(collectionId = null) {
        const title = document.getElementById('photosTitle');
        const subtitle = document.getElementById('photosSubtitle');
        
        if (collectionId && this.currentCollection) {
            title.textContent = `Collection: ${this.currentCollection.name}`;
            subtitle.textContent = 'Photos in this collection';
        } else {
            title.textContent = 'All Photos';
            subtitle.textContent = 'Your complete photo collection';
        }
    }
    
    showPhotoModal(photoId) {
        // Find photo data
        fetch(`/api/photos`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const photo = data.photos.find(p => p.id === photoId);
                    if (photo) {
                        document.getElementById('modalImage').src = photo.cloudinary_secure_url;
                        document.getElementById('modalTitle').textContent = photo.title;
                        document.getElementById('modalDescription').textContent = photo.description || '';
                        document.getElementById('downloadBtn').onclick = () => this.downloadPhotoUrl(photo.cloudinary_secure_url, photo.title);
                        document.getElementById('photoModal').classList.add('active');
                    }
                }
            })
            .catch(error => console.error('Error loading photo:', error));
    }
    
    closeModal() {
        document.getElementById('photoModal').classList.remove('active');
    }
    
    downloadPhotoUrl(url, filename) {
        const link = document.createElement('a');
        link.href = url;
        link.download = filename || 'photo';
        link.target = '_blank';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    // Admin functionality
    async loadAdminData() {
        await this.loadAdminCollections();
        await this.loadAdminPhotos();
    }
    
    async loadAdminCollections() {
        try {
            const response = await fetch('/api/collections');
            const data = await response.json();
            
            if (data.success) {
                this.renderAdminCollections(data.collections);
                this.updateCollectionSelects(data.collections);
            }
        } catch (error) {
            console.error('Error loading admin collections:', error);
        }
    }
    
    async loadAdminPhotos() {
        try {
            const response = await fetch('/api/photos');
            const data = await response.json();
            
            if (data.success) {
                this.renderAdminPhotos(data.photos);
            }
        } catch (error) {
            console.error('Error loading admin photos:', error);
        }
    }
    
    renderAdminCollections(collections) {
        const list = document.getElementById('collectionsList');
        
        if (collections.length === 0) {
            list.innerHTML = '<p class="empty-state">No collections created yet</p>';
            return;
        }
        
        list.innerHTML = collections.map(collection => `
            <div class="collection-item">
                <div>
                    <h4>${this.escapeHtml(collection.name)}</h4>
                    <span>${collection.photo_count} photo${collection.photo_count !== 1 ? 's' : ''}</span>
                </div>
                <button class="btn-danger" onclick="photoGallery.deleteCollection(${collection.id})">Delete</button>
            </div>
        `).join('');
    }
    
    renderAdminPhotos(photos) {
        const list = document.getElementById('adminPhotosList');
        
        if (photos.length === 0) {
            list.innerHTML = '<p class="empty-state">No photos uploaded yet</p>';
            return;
        }
        
        // Store photos for collection options
        this.currentPhotos = photos;
        
        list.innerHTML = photos.map(photo => `
            <div class="admin-photo-item">
                <input type="checkbox" class="photo-checkbox" value="${photo.id}" onchange="photoGallery.updateSelectedPhotos()">
                <img src="${photo.cloudinary_secure_url}" alt="${this.escapeHtml(photo.title)}">
                <div class="admin-photo-info">
                    <h4>${this.escapeHtml(photo.title)}</h4>
                    <p>${this.escapeHtml(photo.description || '')}</p>
                    <p><small>Collection: ${photo.collection_name || 'None'}</small></p>
                </div>
                <div class="admin-photo-actions">
                    <select onchange="photoGallery.updatePhotoCollection(${photo.id}, this.value)">
                        <option value="">No Collection</option>
                        ${this.getCollectionOptionsForPhoto(photo.collection_id)}
                    </select>
                    <button class="btn-danger" onclick="photoGallery.deletePhoto(${photo.id})">Delete</button>
                </div>
            </div>
        `).join('');
    }
    
    updateCollectionSelects(collections) {
        // Store collections for later use
        this.currentCollections = collections;
        
        const selects = ['uploadCollection', 'bulkCollection'];
        
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            const currentValue = select.value;
            
            select.innerHTML = '<option value="">No Collection</option>' +
                collections.map(collection => 
                    `<option value="${collection.id}">${this.escapeHtml(collection.name)}</option>`
                ).join('');
            
            if (currentValue) select.value = currentValue;
        });
    }
    
    getCollectionOptionsForPhoto(selectedId = null) {
        if (!this.currentCollections) return '';
        
        return this.currentCollections.map(collection => 
            `<option value="${collection.id}" ${collection.id === selectedId ? 'selected' : ''}>${this.escapeHtml(collection.name)}</option>`
        ).join('');
    }
    
    // File upload handling
    handleDragOver(e) {
        e.preventDefault();
        e.currentTarget.classList.add('dragover');
    }
    
    handleDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('dragover');
        const files = Array.from(e.dataTransfer.files).filter(file => file.type.startsWith('image/'));
        this.handleFiles(files);
    }
    
    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.handleFiles(files);
    }
    
    handleFiles(files) {
        if (files.length === 0) return;
        
        document.getElementById('uploadForm').style.display = 'block';
        this.renderFilesList(files);
    }
    
    renderFilesList(files) {
        const list = document.getElementById('filesList');
        
        list.innerHTML = files.map((file, index) => `
            <div class="file-item">
                <div class="file-info">
                    <h4>${this.escapeHtml(file.name)}</h4>
                </div>
                <div class="file-inputs">
                    <input type="text" placeholder="Photo title" value="${this.escapeHtml(file.name.split('.')[0])}" data-index="${index}" data-field="title">
                    <input type="text" placeholder="Description" data-index="${index}" data-field="description">
                </div>
            </div>
        `).join('');
        
        // Store files for upload
        this.pendingFiles = files;
    }
    
    async uploadPhotos() {
        if (!this.pendingFiles || this.pendingFiles.length === 0) return;
        
        const formData = new FormData();
        const titles = [];
        const descriptions = [];
        
        // Collect metadata
        document.querySelectorAll('[data-field="title"]').forEach(input => {
            titles.push(input.value || input.placeholder);
        });
        
        document.querySelectorAll('[data-field="description"]').forEach(input => {
            descriptions.push(input.value);
        });
        
        // Add files and metadata
        this.pendingFiles.forEach(file => formData.append('files', file));
        titles.forEach(title => formData.append('titles', title));
        descriptions.forEach(desc => formData.append('descriptions', desc));
        
        const collectionId = document.getElementById('uploadCollection').value;
        if (collectionId) formData.append('collection_id', collectionId);
        
        try {
            const response = await fetch('/api/photos', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast(`Successfully uploaded ${data.photos.length} photos`, 'success');
                this.resetUploadForm();
                this.loadAdminData();
                this.loadCollections();
                this.loadPhotos();
            } else {
                this.showToast(data.error || 'Upload failed', 'error');
            }
        } catch (error) {
            this.showToast('Upload error: ' + error.message, 'error');
        }
    }
    
    resetUploadForm() {
        document.getElementById('uploadForm').style.display = 'none';
        document.getElementById('fileInput').value = '';
        document.getElementById('filesList').innerHTML = '';
        this.pendingFiles = null;
    }
    
    async addCollection() {
        const name = document.getElementById('newCollectionName').value.trim();
        if (!name) return;
        
        try {
            const response = await fetch('/api/collections', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Collection created successfully', 'success');
                document.getElementById('newCollectionName').value = '';
                this.loadAdminCollections();
                this.loadCollections();
            } else {
                this.showToast(data.error || 'Failed to create collection', 'error');
            }
        } catch (error) {
            this.showToast('Error creating collection: ' + error.message, 'error');
        }
    }
    
    async deleteCollection(collectionId) {
        if (!confirm('Are you sure you want to delete this collection? Photos will not be deleted, only unassigned.')) return;
        
        try {
            const response = await fetch(`/api/collections/${collectionId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Collection deleted successfully', 'success');
                this.loadAdminCollections();
                this.loadCollections();
                this.loadPhotos();
            } else {
                this.showToast(data.error || 'Failed to delete collection', 'error');
            }
        } catch (error) {
            this.showToast('Error deleting collection: ' + error.message, 'error');
        }
    }
    
    async deletePhoto(photoId) {
        if (!confirm('Are you sure you want to delete this photo? This action cannot be undone.')) return;
        
        try {
            const response = await fetch(`/api/photos/${photoId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Photo deleted successfully', 'success');
                this.loadAdminData();
                this.loadCollections();
                this.loadPhotos();
            } else {
                this.showToast(data.error || 'Failed to delete photo', 'error');
            }
        } catch (error) {
            this.showToast('Error deleting photo: ' + error.message, 'error');
        }
    }
    
    async updatePhotoCollection(photoId, collectionId) {
        try {
            const response = await fetch(`/api/photos/${photoId}/collection`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ collection_id: collectionId || null })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Photo collection updated', 'success');
                this.loadAdminData();
                this.loadCollections();
            } else {
                this.showToast(data.error || 'Failed to update photo collection', 'error');
            }
        } catch (error) {
            this.showToast('Error updating photo collection: ' + error.message, 'error');
        }
    }
    
    updateSelectedPhotos() {
        this.selectedPhotos.clear();
        document.querySelectorAll('.photo-checkbox:checked').forEach(checkbox => {
            this.selectedPhotos.add(parseInt(checkbox.value));
        });
    }
    
    toggleSelectAll(e) {
        const checkboxes = document.querySelectorAll('.photo-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.checked = e.target.checked;
        });
        this.updateSelectedPhotos();
    }
    
    async bulkAssignCollection() {
        if (this.selectedPhotos.size === 0) {
            this.showToast('No photos selected', 'error');
            return;
        }
        
        const collectionId = document.getElementById('bulkCollection').value;
        
        try {
            const response = await fetch('/api/photos/bulk-update', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    photo_ids: Array.from(this.selectedPhotos),
                    collection_id: collectionId || null
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast(`Updated ${data.updated_count} photos`, 'success');
                this.selectedPhotos.clear();
                document.getElementById('selectAllPhotos').checked = false;
                this.loadAdminData();
                this.loadCollections();
            } else {
                this.showToast(data.error || 'Failed to update photos', 'error');
            }
        } catch (error) {
            this.showToast('Error updating photos: ' + error.message, 'error');
        }
    }
    
    async bulkDeletePhotos() {
        if (this.selectedPhotos.size === 0) {
            this.showToast('No photos selected', 'error');
            return;
        }
        
        if (!confirm(`Are you sure you want to delete ${this.selectedPhotos.size} photos? This action cannot be undone.`)) return;
        
        try {
            const response = await fetch('/api/photos/bulk-delete', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    photo_ids: Array.from(this.selectedPhotos)
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast(`Deleted ${data.deleted_count} photos`, 'success');
                this.selectedPhotos.clear();
                document.getElementById('selectAllPhotos').checked = false;
                this.loadAdminData();
                this.loadCollections();
                this.loadPhotos();
            } else {
                this.showToast(data.error || 'Failed to delete photos', 'error');
            }
        } catch (error) {
            this.showToast('Error deleting photos: ' + error.message, 'error');
        }
    }
    
    // Utility functions
    showEmptyState(containerId, title, subtitle) {
        const container = document.getElementById(containerId);
        container.innerHTML = `
            <div class="empty-state">
                <h3>${title}</h3>
                <p>${subtitle}</p>
            </div>
        `;
    }
    
    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 100);
        
        // Remove after 5 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => container.removeChild(toast), 300);
        }, 5000);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the photo gallery
const photoGallery = new PhotoGallery();

