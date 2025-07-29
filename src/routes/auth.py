import os
from flask import Blueprint, request, jsonify, session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/auth/login', methods=['POST'])
def login():
    """Admin login endpoint"""
    try:
        data = request.get_json()
        password = data.get('password', '')
        
        admin_password = os.getenv('ADMIN_PASSWORD', 'Hanshow99@')
        
        if password == admin_password:
            session['admin_logged_in'] = True
            return jsonify({
                'success': True,
                'message': 'Login successful'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid password'
            }), 401
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@auth_bp.route('/auth/logout', methods=['POST'])
def logout():
    """Admin logout endpoint"""
    try:
        session.pop('admin_logged_in', None)
        return jsonify({
            'success': True,
            'message': 'Logout successful'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@auth_bp.route('/auth/status', methods=['GET'])
def auth_status():
    """Check if admin is logged in"""
    try:
        is_logged_in = session.get('admin_logged_in', False)
        return jsonify({
            'success': True,
            'logged_in': is_logged_in
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def require_admin_auth(f):
    """Decorator to require admin authentication"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in', False):
            return jsonify({
                'success': False,
                'error': 'Admin authentication required'
            }), 401
        return f(*args, **kwargs)
    return decorated_function

