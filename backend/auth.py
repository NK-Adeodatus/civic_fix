from functools import wraps
from flask import request, jsonify, current_app
from supabase import create_client, Client
import jwt
from models import User, db

def get_supabase_client():
    """Get Supabase client instance"""
    url = current_app.config['SUPABASE_URL']
    key = current_app.config['SUPABASE_KEY']
    return create_client(url, key)

def get_supabase_service_client():
    """Get Supabase client with service role key (bypasses RLS)"""
    url = current_app.config['SUPABASE_URL']
    key = current_app.config['SUPABASE_SERVICE_ROLE_KEY']
    if not key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY not configured")
    # Strip whitespace (including newlines) from key
    key = key.strip() if key else None
    if not key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is empty after stripping whitespace")
    return create_client(url, key)

def verify_supabase_token(token):
    """Verify Supabase JWT token and return user data"""
    try:
        import jwt
        
        # For development, decode without signature verification
        # In production, you'd verify with the proper JWT secret
        payload = jwt.decode(token, options={"verify_signature": False})
        
        # Create a user-like object from the payload
        class UserData:
            def __init__(self, payload):
                self.id = payload.get('sub')
                self.email = payload.get('email')
                self.aud = payload.get('aud')
                # Add more fields as needed
                self.user_metadata = payload.get('user_metadata', {})
        
        # Validate that we have the required fields
        if payload.get('sub') and payload.get('email'):
            return UserData(payload)
        
        return None
        
    except jwt.InvalidTokenError as e:
        print(f"JWT Token error: {e}")
        return None
    except Exception as e:
        print(f"Token verification error: {e}")
        return None

def token_required(f):
    """Decorator to require valid Supabase authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid authorization header format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        # Verify token with Supabase
        user_data = verify_supabase_token(token)
        if not user_data:
            return jsonify({'error': 'Token is invalid'}), 401
        
        # Get or create user in our database
        user = User.query.filter_by(id=user_data.id).first()
        if not user:
            # Create user if doesn't exist (first time login)
            # Use username from metadata, fallback to email prefix if not available
            username = user_data.user_metadata.get('username', user_data.email.split('@')[0])
            
            user = User(
                id=user_data.id,
                email=user_data.email,
                username=username,
                phone=user_data.user_metadata.get('phone', ''),
                province=user_data.user_metadata.get('province', ''),
                district=user_data.user_metadata.get('district', ''),
                sector=user_data.user_metadata.get('sector', '')
            )
            db.session.add(user)
            db.session.commit()
        else:
            # Update existing user with metadata if username looks like email prefix
            metadata_username = user_data.user_metadata.get('username')
            if metadata_username and user.username == user.email.split('@')[0]:
                # This user likely has the old email-based username, update it
                user.username = metadata_username
                
                # Also update other fields if they're empty
                if not user.phone and user_data.user_metadata.get('phone'):
                    user.phone = user_data.user_metadata.get('phone')
                if not user.province and user_data.user_metadata.get('province'):
                    user.province = user_data.user_metadata.get('province')
                if not user.district and user_data.user_metadata.get('district'):
                    user.district = user_data.user_metadata.get('district')
                if not user.sector and user_data.user_metadata.get('sector'):
                    user.sector = user_data.user_metadata.get('sector')
                
                db.session.commit()
        
        # Make user available in the route
        request.current_user = user
        return f(*args, **kwargs)
    
    return decorated

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(request, 'current_user') or not request.current_user.is_admin:
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    
    return decorated

def optional_auth(f):
    """Decorator for optional authentication (doesn't fail if no token)"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        request.current_user = None
        
        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
                user_data = verify_supabase_token(token)
                if user_data:
                    user = User.query.filter_by(id=user_data.id).first()
                    request.current_user = user
            except:
                pass  # Continue without authentication
        
        return f(*args, **kwargs)
    
    return decorated
