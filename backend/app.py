import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename
from PIL import Image
import uuid
import random
import smtplib
import jwt
import bcrypt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from sqlalchemy import text

from config import Config
from models import db, User, Issue, Vote, Notification, StatusHistory, AdminComment
from auth import token_required, admin_required, optional_auth, get_supabase_client, get_supabase_service_client

# Global SocketIO instance (initialized in create_app)
socketio = None


def generate_verification_code():
    return str(random.randint(100000, 999999))

def send_verification_email(email, code, username):
    """Send verification code email to user"""
    try:
        print(f"=== SENDING EMAIL TO {email} ===")
        
        # Email configuration (you'll need to set these in your .env file)
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        smtp_username = os.environ.get('SMTP_USERNAME')
        smtp_password = os.environ.get('SMTP_PASSWORD')
        from_email = os.environ.get('FROM_EMAIL', smtp_username)
        
        print(f"SMTP Config - Server: {smtp_server}, Port: {smtp_port}")
        print(f"SMTP Username: {smtp_username}")
        print(f"From Email: {from_email}")
        print(f"SMTP Password configured: {'Yes' if smtp_password else 'No'}")
        
        if not smtp_username or not smtp_password:
            print("SMTP credentials not configured. Email not sent.")
            return False
        
        # Create message
        print("Creating email message...")
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = email
        msg['Subject'] = "CivicFix - Email Verification Code"
        
        # Email body
        body = f"""
        Hello {username},
        
        Welcome to CivicFix Rwanda! 
        
        To complete your registration, please use the following verification code:
        
        Verification Code: {code}
        
        This code will expire in 15 minutes.
        
        If you didn't create an account with CivicFix, please ignore this email.
        
        Best regards,
        CivicFix Team
        """
        
        msg.attach(MIMEText(body, 'plain'))
        print("Email message created successfully")
        
        # Send email
        print("Connecting to SMTP server...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        print("Starting TLS...")
        server.starttls()
        print("Logging in to SMTP server...")
        server.login(smtp_username, smtp_password)
        print("Sending email...")
        text = msg.as_string()
        server.sendmail(from_email, email, text)
        server.quit()
        
        print(f"Verification email sent successfully to {email}")
        return True
        
    except Exception as e:
        print(f"ERROR sending email: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_app():
    # Serve frontend from parent directory
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend-web')
    app = Flask(__name__, static_folder=frontend_path, static_url_path='')
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Initialize Socket.IO on the same app/port to avoid conflicts
    # Disabled for production - using HTTP polling instead to avoid worker timeouts
    global socketio
    socketio = None
    # socketio = SocketIO(
    #     app, 
    #     cors_allowed_origins="*",
    #     async_mode='threading',
    #     ping_timeout=120,
    #     ping_interval=25,
    #     engineio_logger=False,
    #     socketio_logger=False
    # )
    
    # Configure CORS - Allow all origins for development
    CORS(app, origins="*", allow_headers=["Content-Type", "Authorization"], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    
    # Initialize rate limiter
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["1000 per day", "200 per hour"]
    )
    limiter.init_app(app)
    
    # Create upload directory
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), app.config['UPLOAD_FOLDER'])
    os.makedirs(upload_dir, exist_ok=True)
    
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    
    def resize_image(image_path, max_size=(800, 600)):
        """Resize image to reduce file size while maintaining quality"""
        try:
            with Image.open(image_path) as img:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                img.save(image_path, optimize=True, quality=85)
        except Exception as e:
            print(f"Error resizing image: {e}")
    
    def upload_to_supabase_storage(file, bucket_name='issue-images'):
        """Upload image to Supabase Storage and return public URL"""
        try:
            print(f"[IMAGE UPLOAD] Starting upload for file: {file.filename}")
            
            supabase = get_supabase_service_client()
            print(f"[IMAGE UPLOAD] Supabase service client initialized")
            
            # Generate unique filename
            filename = secure_filename(file.filename)
            filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{filename}"
            print(f"[IMAGE UPLOAD] Generated filename: {filename}")
            
            # Read file content
            file_content = file.read()
            print(f"[IMAGE UPLOAD] File size: {len(file_content)} bytes")
            
            # Reset file pointer for potential re-read
            file.seek(0)
            
            # Upload to Supabase Storage
            print(f"[IMAGE UPLOAD] Uploading to bucket: {bucket_name}")
            response = supabase.storage.from_(bucket_name).upload(
                path=filename,
                file=file_content,
                file_options={"content-type": file.content_type}
            )
            print(f"[IMAGE UPLOAD] Upload response: {response}")
            
            # Get public URL
            public_url = supabase.storage.from_(bucket_name).get_public_url(filename)
            print(f"[IMAGE UPLOAD] Public URL: {public_url}")
            
            if not public_url:
                print(f"[IMAGE UPLOAD] ERROR: Failed to get public URL")
                return None
            
            print(f"[IMAGE UPLOAD] SUCCESS: Image uploaded to {public_url}")
            return public_url
            
        except Exception as e:
            print(f"[IMAGE UPLOAD] ERROR: {str(e)}")
            import traceback
            print(f"[IMAGE UPLOAD] Traceback: {traceback.format_exc()}")
            return None
    
    # Routes
    @app.route('/')
    def index():
        """Serve index.html for root path"""
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.route('/api/status')
    def api_status():
        """API status endpoint"""
        return jsonify({"status": "CivicFix API is operational"})
    
    # Email Verification Routes
    @app.route('/api/auth/send-verification', methods=['POST'])
    def send_verification():
        """Send verification code to user email"""
        try:
            print("=== SEND VERIFICATION ENDPOINT CALLED ===")
            data = request.get_json()
            print(f"Request data: {data}")
            
            email = data.get('email')
            username = data.get('username')
            user_id = data.get('user_id')
            phone = data.get('phone', '')
            province = data.get('province', '')
            district = data.get('district', '')
            sector = data.get('sector', '')
            
            print(f"Extracted data - Email: {email}, Username: {username}, User ID: {user_id}")
            
            if not email or not username or not user_id:
                print("Missing required fields")
                return jsonify({'error': 'Missing required fields'}), 400
            
            # Generate verification code
            verification_code = generate_verification_code()
            expires_at = datetime.utcnow() + timedelta(minutes=15)  # 15 minutes expiry
            print(f"Generated verification code: {verification_code}")
            
            # Create or update user record in our database
            print("Creating/updating user in database...")
            print(f"DEBUG: Checking for existing user with email: {email}")
            
            # First check by email (since email must be unique)
            user = User.query.filter_by(email=email).first()
            print(f"DEBUG: User found by email: {user is not None}")
            
            if not user:
                # Check by user_id as well
                print(f"DEBUG: No user found by email, checking by user_id: {user_id}")
                user = User.query.filter_by(id=user_id).first()
                print(f"DEBUG: User found by user_id: {user is not None}")
            
            if not user:
                # Check if user exists in auth.users with this email
                print("DEBUG: Checking auth.users for existing user with this email")
                try:
                    auth_user_result = db.session.execute(text("SELECT id FROM auth.users WHERE email = :email"), {"email": email})
                    auth_user = auth_user_result.fetchone()
                    print(f"DEBUG: auth.users query result: {auth_user}")
                except Exception as auth_error:
                    print(f"DEBUG: Error querying auth.users: {auth_error}")
                    auth_user = None
                
                if auth_user:
                    # Use the existing auth.users ID
                    actual_user_id = auth_user[0]
                    print(f"DEBUG: Found existing auth user with ID: {actual_user_id}")
                    
                    user = User(
                        id=actual_user_id,  # Use the correct ID from auth.users
                        username=username,
                        email=email,
                        phone=phone,
                        province=province,
                        district=district,
                        sector=sector,
                        is_email_verified=False,
                        verification_code=verification_code,
                        verification_code_expires=expires_at
                    )
                    db.session.add(user)
                    print("Creating new user with existing auth.users ID")
                else:
                    print("Creating new user with provided ID")
                    user = User(
                        id=user_id,
                        username=username,
                        email=email,
                        phone=phone,
                        province=province,
                        district=district,
                        sector=sector,
                        is_email_verified=False,
                        verification_code=verification_code,
                        verification_code_expires=expires_at
                    )
                    db.session.add(user)
            else:
                print(f"Updating existing user")
                # Update user data
                user.username = username
                user.phone = phone
                user.province = province
                user.district = district
                user.sector = sector
                user.verification_code = verification_code
                user.verification_code_expires = expires_at
                user.is_email_verified = False
            
            db.session.commit()
            print("User saved to database successfully")
            
            # SMTP is disabled - Supabase handles email confirmation
            print("SMTP disabled - Supabase will send confirmation email")
            print("Verification code stored in database for backup verification")
            
            return jsonify({'message': 'Account created! Check your email from Supabase to confirm signup.'})
                
        except Exception as e:
            db.session.rollback()
            print(f"ERROR in send_verification: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Server error: {str(e)}'}), 500
    
    @app.route('/api/auth/verify-email', methods=['POST'])
    def verify_email():
        """Verify email with code"""
        try:
            print("=== VERIFY EMAIL ENDPOINT CALLED ===")
            data = request.get_json()
            print(f"Request data: {data}")
            
            email = data.get('email')
            verification_code = data.get('verification_code')
            
            print(f"Email: {email}, Code: {verification_code}")
            
            if not email or not verification_code:
                print("Missing email or verification code")
                return jsonify({'error': 'Email and verification code are required'}), 400
            
            # Find user by email
            print(f"Looking for user with email: {email}")
            user = User.query.filter_by(email=email).first()
            if not user:
                print("User not found")
                return jsonify({'error': 'User not found'}), 404
            
            print(f"User found: {user.username}")
            print(f"Stored code: {user.verification_code}")
            print(f"Provided code: {verification_code}")
            print(f"Code expires: {user.verification_code_expires}")
            # Get current time for comparison (handle timezone issues)
            import datetime as dt
            current_time = dt.datetime.utcnow()
            print(f"Current time: {current_time}")
            
            # Check if code is valid and not expired
            if user.verification_code != verification_code:
                print("Verification code mismatch")
                return jsonify({'error': 'Invalid verification code'}), 400
            
            if not user.verification_code_expires:
                print("No expiration time set")
                return jsonify({'error': 'Invalid verification code'}), 400
                
            # Compare datetimes (convert timezone-aware to naive if needed)
            expires_time = user.verification_code_expires
            if hasattr(expires_time, 'tzinfo') and expires_time.tzinfo is not None:
                expires_time = expires_time.replace(tzinfo=None)
            
            if expires_time < current_time:
                print("Verification code expired")
                return jsonify({'error': 'Verification code has expired'}), 400
            
            # Mark email as verified
            print("Marking email as verified")
            user.is_email_verified = True
            user.verification_code = None
            user.verification_code_expires = None
            db.session.commit()
            
            print("Email verified successfully")
            return jsonify({'message': 'Email verified successfully'})
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR in verify_email: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Server error. Please try again.'}), 500
    
    @app.route('/api/auth/resend-verification', methods=['POST'])
    def resend_verification():
        """Resend verification code (SMTP disabled - Supabase handles emails)"""
        try:
            data = request.get_json()
            email = data.get('email')
            
            if not email:
                return jsonify({'error': 'Email is required'}), 400
            
            # Find user by email
            user = User.query.filter_by(email=email).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            if user.is_email_verified:
                return jsonify({'error': 'Email is already verified'}), 400
            
            # SMTP is disabled - Supabase handles email resending
            print(f"Resend verification requested for {email} - SMTP disabled, Supabase handles emails")
            return jsonify({'message': 'Check your email from Supabase for the confirmation link.'})
        except Exception as e:
            print(f"Error in resend_verification: {e}")
            return jsonify({'error': 'Server error. Please try again.'}), 500
    
    # Authentication routes (handled by Supabase on frontend)
    @app.route('/api/auth/verify', methods=['GET', 'POST'])
    @token_required
    def verify_auth():
        """Verify authentication and return user info"""
        return jsonify({
            'user': request.current_user.to_dict(),
            'message': 'Authentication verified'
        })
    
    @app.route('/api/auth/check-verification', methods=['POST'])
    def check_verification():
        """Check if user's email is verified in our system"""
        try:
            data = request.get_json()
            email = data.get('email')
            
            if not email:
                return jsonify({'error': 'Email is required'}), 400
            
            user = User.query.filter_by(email=email).first()
            if not user:
                return jsonify({'is_verified': False}), 200
            
            return jsonify({'is_verified': user.is_email_verified}), 200
            
        except Exception as e:
            print(f"Error checking verification: {e}")
            return jsonify({'error': 'Server error'}), 500
    
    @app.route('/api/auth/mark-verified', methods=['POST'])
    def mark_verified():
        """Mark user's email as verified (called after Supabase confirms email)"""
        try:
            data = request.get_json()
            email = data.get('email')
            
            if not email:
                return jsonify({'error': 'Email is required'}), 400
            
            print(f"[mark-verified] Marking email as verified: {email}")
            user = User.query.filter_by(email=email).first()
            if not user:
                print(f"[mark-verified] User not found: {email}")
                return jsonify({'error': 'User not found'}), 404
            
            # Mark email as verified
            user.is_email_verified = True
            user.verification_code = None
            user.verification_code_expires = None
            db.session.commit()
            
            print(f"[mark-verified] Email marked as verified: {email}")
            return jsonify({'message': 'Email marked as verified', 'is_verified': True}), 200
            
        except Exception as e:
            db.session.rollback()
            print(f"[mark-verified] Error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Server error'}), 500
    
    @app.route('/api/auth/backend-login', methods=['POST'])
    def backend_login():
        """Backend-only login for verified users when Supabase fails"""
        try:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
            
            if not email or not password:
                return jsonify({'error': 'Email and password are required'}), 400
            
            # Check if user exists and is verified
            user = User.query.filter_by(email=email).first()
            if not user or not user.is_email_verified:
                return jsonify({'error': 'Invalid credentials or email not verified'}), 401
            
            # For verified users, we'll bypass Supabase password check
            # and create a token directly (since email is already verified in our system)
            try:
                # Create a JWT token for the verified user
                token = jwt.encode({
                    'user_id': user.id,
                    'email': user.email,
                    'exp': datetime.utcnow() + timedelta(hours=24)
                }, app.config['SECRET_KEY'], algorithm='HS256')
                
                print(f"Backend login successful for verified user: {user.email}")
                
                return jsonify({
                    'token': token,
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'username': user.username
                    }
                }), 200
                    
            except Exception as token_error:
                print(f"Token generation error: {token_error}")
                return jsonify({'error': 'Authentication failed'}), 401
            
        except Exception as e:
            print(f"Error in backend login: {e}")
            return jsonify({'error': 'Server error'}), 500
    
    # Issue routes
    @app.route('/api/issues', methods=['GET'])
    @limiter.exempt  # Exempt from rate limiting since this is polled frequently by auto-refresh
    @optional_auth
    def get_issues():
        """Get all issues with optional filtering and search"""
        try:
            print(f"[GET /api/issues] Request received with args: {request.args}")
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            status = request.args.get('status')
            category = request.args.get('category')
            province = request.args.get('province')
            district = request.args.get('district')
            sector = request.args.get('sector')
            search = request.args.get('search')
            
            query = Issue.query
            
            if status:
                query = query.filter(Issue.status == status)
            if category:
                query = query.filter(Issue.category == category)
            if province:
                # Filter by issue province
                query = query.filter(Issue.province == province)
            if district:
                # Filter by issue district
                query = query.filter(Issue.district == district)
            if sector:
                # Filter by issue sector
                query = query.filter(Issue.sector == sector)
            if search:
                # Search in title, description, location fields
                search_term = f"%{search}%"
                query = query.filter(
                    db.or_(
                        Issue.title.ilike(search_term),
                        Issue.description.ilike(search_term),
                        Issue.street_address.ilike(search_term),
                        Issue.landmark_reference.ilike(search_term),
                        Issue.detailed_description.ilike(search_term),
                        Issue.province.ilike(search_term),
                        Issue.district.ilike(search_term),
                        Issue.sector.ilike(search_term)
                    )
                )
            
            issues = query.order_by(Issue.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            print(f"[GET /api/issues] Returning {len(issues.items)} issues")
            return jsonify({
                'issues': [issue.to_dict() for issue in issues.items],
                'total': issues.total,
                'pages': issues.pages,
                'current_page': page
            })
        except Exception as e:
            print(f"[GET /api/issues] ERROR: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/issues/<int:issue_id>', methods=['GET'])
    @optional_auth
    def get_issue(issue_id):
        """Get single issue details"""
        issue = Issue.query.get_or_404(issue_id)
        return jsonify(issue.to_dict())
    
    @app.route('/api/issues', methods=['POST'])
    @token_required
    @limiter.limit("5 per minute")
    def create_issue():
        """Create new issue report"""
        try:
            # Handle both JSON and form data
            if request.content_type and 'multipart/form-data' in request.content_type:
                data = request.form.to_dict()
            else:
                data = request.get_json()
            
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Validate required fields
            required_fields = ['title', 'description', 'category']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'{field} is required'}), 400
            
            # Handle image upload to Supabase Storage
            image_url = None
            print(f"[CREATE ISSUE] Checking for image in request.files")
            print(f"[CREATE ISSUE] request.files keys: {list(request.files.keys())}")
            
            if 'image' in request.files:
                file = request.files['image']
                print(f"[CREATE ISSUE] Image file found: {file.filename}")
                
                if file and file.filename:
                    print(f"[CREATE ISSUE] File has content, checking if allowed")
                    if allowed_file(file.filename):
                        print(f"[CREATE ISSUE] File type allowed, uploading to Supabase")
                        # Upload to Supabase Storage
                        image_url = upload_to_supabase_storage(file)
                        if image_url:
                            print(f"[CREATE ISSUE] Image uploaded successfully: {image_url}")
                        else:
                            print(f"[CREATE ISSUE] Warning: Image upload to Supabase failed, continuing without image")
                    else:
                        print(f"[CREATE ISSUE] File type not allowed: {file.filename}")
            else:
                print(f"[CREATE ISSUE] No image in request.files")
            
            # Verify user is authenticated
            if not hasattr(request, 'current_user') or not request.current_user:
                return jsonify({'error': 'User not authenticated'}), 401
            
            if not hasattr(request.current_user, 'id') or not request.current_user.id:
                return jsonify({'error': 'Invalid user data'}), 401
            
            # Create issue
            issue = Issue(
                title=data['title'],
                description=data['description'],
                category=data['category'],
                street_address=data.get('street_address', ''),
                landmark_reference=data.get('landmark_reference', ''),
                detailed_description=data.get('detailed_description', ''),
                province=data.get('province', ''),
                district=data.get('district', ''),
                sector=data.get('sector', ''),
                image_url=image_url,
                user_id=request.current_user.id
            )
            
            db.session.add(issue)
            db.session.commit()
            
            # Notify admins and all connected clients about the new issue
            # Socket.IO is disabled for production, so we skip real-time notifications
            # try:
            #     payload = {
            #         'type': 'new_issue',
            #         'message': f"New issue reported: {issue.title}",
            #         'issue': issue.to_dict()
            #     }

            #     # Existing behaviour: notify admins watching the dashboard
            #     socketio.emit('admin_update', payload, room='admins')

            #     # New behaviour: broadcast generic new_issue event to everyone
            #     # (citizens on the main feed, admins, and any other listeners)
            #     socketio.emit('new_issue', payload, broadcast=True)
            # except Exception as socket_error:
            #     print(f"SocketIO error (non-critical): {socket_error}")
            
            return jsonify({
                'message': 'Issue created successfully',
                'issue': issue.to_dict()
            }), 201
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating issue: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Server error: {str(e)}'}), 500
    
    @app.route('/api/issues/<int:issue_id>', methods=['DELETE'])
    @token_required
    def delete_issue(issue_id):
        """Delete an issue (only by the user who created it)"""
        try:
            issue = Issue.query.get_or_404(issue_id)
            
            # Check if the current user is the owner of the issue
            if issue.user_id != request.current_user.id:
                return jsonify({'error': 'You can only delete your own issues'}), 403
            
            # Delete image from Supabase Storage if it exists and is a Supabase URL
            if issue.image_url:
                try:
                    # Only delete if it's a Supabase Storage URL (starts with https://)
                    if issue.image_url.startswith('https://'):
                        # Extract the file path from the Supabase URL
                        # URL format: https://ozaaasesvvjphzohfxoo.supabase.co/storage/v1/object/public/issue-images/filename
                        # We need to extract just the filename
                        url_parts = issue.image_url.split('/issue-images/')
                        if len(url_parts) > 1:
                            filename = url_parts[1]
                            supabase = get_supabase_service_client()
                            supabase.storage.from_('issue-images').remove([filename])
                            print(f"[DELETE ISSUE] Deleted image from Supabase: {filename}")
                except Exception as img_error:
                    # Log the error but don't fail the entire delete operation
                    print(f"[DELETE ISSUE] Warning: Could not delete image from Supabase: {str(img_error)}")
            
            # Delete associated votes first
            Vote.query.filter_by(issue_id=issue_id).delete()
            
            # Delete associated notifications
            Notification.query.filter_by(issue_id=issue_id).delete()
            
            # Delete the issue
            db.session.delete(issue)
            db.session.commit()
            
            return jsonify({'message': 'Issue deleted successfully'})
            
        except Exception as e:
            db.session.rollback()
            print(f"[DELETE ISSUE] Error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/issues/<int:issue_id>', methods=['PUT'])
    @token_required
    def update_issue(issue_id):
        """Update an issue (only by the user who created it)"""
        try:
            issue = Issue.query.get_or_404(issue_id)
            
            # Check if the current user is the owner of the issue
            if issue.user_id != request.current_user.id:
                return jsonify({'error': 'You can only edit your own issues'}), 403
            
            # Get form data
            title = request.form.get('title')
            description = request.form.get('description')
            category = request.form.get('category')
            street_address = request.form.get('street_address')
            landmark_reference = request.form.get('landmark_reference')
            detailed_description = request.form.get('detailed_description')
            
            # Validate required fields
            if not all([title, description, category]):
                return jsonify({'error': 'Title, description, and category are required'}), 400
            
            # Update issue fields
            issue.title = title
            issue.description = description
            issue.category = category
            issue.street_address = street_address
            issue.landmark_reference = landmark_reference
            issue.detailed_description = detailed_description
            issue.updated_at = datetime.utcnow()
            
            # Handle image upload if provided
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    # Upload new image to Supabase Storage
                    new_image_url = upload_to_supabase_storage(file)
                    if new_image_url:
                        issue.image_url = new_image_url
                    else:
                        print("Warning: Image upload to Supabase failed, keeping old image")
            
            db.session.commit()
            
            return jsonify({
                'message': 'Issue updated successfully',
                'issue': issue.to_dict()
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/issues/<int:issue_id>/status', methods=['PATCH'])
    @token_required
    @admin_required
    def update_issue_status(issue_id):
        """Admin: Update issue status"""
        try:
            data = request.get_json()
            new_status = data.get('status')
            
            if not new_status or new_status not in ['Open', 'In Progress', 'Resolved']:
                return jsonify({'error': 'Invalid status'}), 400
            
            issue = Issue.query.get_or_404(issue_id)
            old_status = issue.status
            issue.status = new_status
            issue.updated_at = datetime.utcnow()
            
            # Create notification for the reporter
            if old_status != new_status:
                notification = Notification(
                    user_id=issue.user_id,
                    message=f"Your issue '{issue.title}' status changed from {old_status} to {new_status}",
                    issue_id=issue.id
                )
                db.session.add(notification)
            
            db.session.commit()
            
            # Send real-time notification to the issue reporter
            # Socket.IO disabled - real-time notifications skipped
            # if old_status != new_status:
            #     socketio.emit('status_update', {
            #         'message': f"Your issue '{issue.title}' status changed to {new_status}",
            #         'issue_id': issue.id,
            #         'new_status': new_status,
            #         'issue': issue.to_dict()
            #     }, room=f"user_{issue.user_id}")
            #     
            #     # Notify all admins about the status change
            #     socketio.emit('admin_update', {
            #         'type': 'status_change',
            #         'message': f"Issue #{issue.id} status changed to {new_status}",
            #         'issue': issue.to_dict()
            #     }, room='admins')
            
            return jsonify({
                'message': 'Issue status updated successfully',
                'issue': issue.to_dict()
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    # Vote routes
    @app.route('/api/issues/<int:issue_id>/vote', methods=['POST'])
    @token_required
    @limiter.limit("10 per minute")
    def vote_issue(issue_id):
        """Vote/Unvote toggle on an issue"""
        try:
            issue = Issue.query.get_or_404(issue_id)
            
            # Check if user already voted
            existing_vote = Vote.query.filter_by(
                user_id=request.current_user.id,
                issue_id=issue_id
            ).first()
            
            if existing_vote:
                # Remove existing vote (unvote)
                db.session.delete(existing_vote)
                db.session.commit()
                
                # Send real-time vote update to all users
                # Socket.IO disabled - real-time notifications skipped
                # socketio.emit('vote_update', {
                #     'issue_id': issue_id,
                #     'vote_count': issue.vote_count,
                #     'issue_owner_id': str(issue.user_id),  # Include issue owner ID for smart notifications
                #     'message': f"Vote removed from issue #{issue_id}"
                # })
                
                return jsonify({
                    'message': 'Vote removed successfully',
                    'action': 'unvoted',
                    'vote_count': issue.vote_count
                })
            else:
                # Create new vote
                vote = Vote(
                    user_id=request.current_user.id,
                    issue_id=issue_id
                )
                db.session.add(vote)
                db.session.commit()
                
                # Send real-time vote update to all users
                # Socket.IO disabled - real-time notifications skipped
                # socketio.emit('vote_update', {
                #     'issue_id': issue_id,
                #     'vote_count': issue.vote_count,
                #     'issue_owner_id': str(issue.user_id),  # Include issue owner ID for smart notifications
                #     'message': f"Issue #{issue_id} received a new vote"
                # })
                
                return jsonify({
                    'message': 'Vote recorded successfully',
                    'action': 'voted',
                    'vote_count': issue.vote_count
                })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/issues/<int:issue_id>/votes', methods=['GET'])
    def get_issue_votes(issue_id):
        """Get vote count for an issue"""
        issue = Issue.query.get_or_404(issue_id)
        return jsonify({'vote_count': issue.vote_count})
    
    # User profile routes
    @app.route('/api/user/profile', methods=['GET'])
    @token_required
    def get_user_profile():
        """Get current user's profile"""
        try:
            user = User.query.filter_by(id=request.current_user.id).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            return jsonify(user.to_dict())
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/user/profile', methods=['PUT'])
    @token_required
    def update_user_profile():
        """Update current user's profile"""
        try:
            user = User.query.filter_by(id=request.current_user.id).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            data = request.get_json()
            
            # Update allowed fields
            if 'username' in data:
                user.username = data['username']
            if 'phone' in data:
                user.phone = data['phone']
            if 'province' in data:
                user.province = data['province']
            if 'district' in data:
                user.district = data['district']
            if 'sector' in data:
                user.sector = data['sector']
            
            db.session.commit()
            return jsonify({'message': 'Profile updated successfully'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/user/issues', methods=['GET'])
    @token_required
    def get_user_issues():
        """Get current user's submitted issues"""
        try:
            issues = Issue.query.filter_by(user_id=request.current_user.id)\
                               .order_by(Issue.created_at.desc()).all()
            
            return jsonify({
                'issues': [issue.to_dict() for issue in issues],
                'total': len(issues)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/user/stats', methods=['GET'])
    @token_required
    def get_user_stats():
        """Get current user's voting and activity statistics"""
        try:
            user_id = request.current_user.id
            
            # Count votes given by user
            votes_given = Vote.query.filter_by(user_id=user_id).count()
            
            # Count votes received on user's issues
            votes_received = db.session.query(Vote).join(Issue).filter(Issue.user_id == user_id).count()
            
            # Get user's issues count
            issues_submitted = Issue.query.filter_by(user_id=user_id).count()
            
            # Get recent activity (last 10 votes by user)
            recent_votes = db.session.query(Vote, Issue).join(Issue).filter(Vote.user_id == user_id).order_by(Vote.created_at.desc()).limit(10).all()
            
            recent_activity = []
            for vote, issue in recent_votes:
                recent_activity.append({
                    'type': 'vote',
                    'issue_title': issue.title,
                    'issue_id': issue.id,
                    'created_at': vote.created_at.isoformat()
                })
            
            return jsonify({
                'votes_given': votes_given,
                'votes_received': votes_received,
                'issues_submitted': issues_submitted,
                'recent_activity': recent_activity
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/user/account', methods=['DELETE'])
    @token_required
    def delete_user_account():
        """Delete current user's account"""
        try:
            user = User.query.filter_by(id=request.current_user.id).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Delete user's votes
            Vote.query.filter_by(user_id=user.id).delete()
            
            # Delete user's notifications
            Notification.query.filter_by(user_id=user.id).delete()
            
            # Delete user's issues
            Issue.query.filter_by(user_id=user.id).delete()
            
            # Delete user
            db.session.delete(user)
            db.session.commit()
            
            return jsonify({'message': 'Account deleted successfully'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    # Notification routes
    @app.route('/api/notifications', methods=['GET'])
    @token_required
    def get_notifications():
        """Get user's notifications"""
        notifications = Notification.query.filter_by(
            user_id=request.current_user.id
        ).order_by(Notification.created_at.desc()).all()
        
        return jsonify({
            'notifications': [notification.to_dict() for notification in notifications]
        })
    
    @app.route('/api/notifications/<int:notification_id>/read', methods=['PATCH'])
    @token_required
    def mark_notification_read(notification_id):
        """Mark notification as read"""
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=request.current_user.id
        ).first_or_404()
        
        notification.is_read = True
        db.session.commit()
        
        return jsonify({'message': 'Notification marked as read'})
    
    # Admin routes
    @app.route('/api/admin/dashboard', methods=['GET'])
    @token_required
    @admin_required
    def admin_dashboard():
        """Admin dashboard statistics"""
        total_issues = Issue.query.count()
        open_issues = Issue.query.filter_by(status='Open').count()
        in_progress_issues = Issue.query.filter_by(status='In Progress').count()
        resolved_issues = Issue.query.filter_by(status='Resolved').count()
        
        # Get recent issues
        recent_issues = Issue.query.order_by(Issue.created_at.desc()).limit(10).all()
        
        return jsonify({
            'stats': {
                'total_issues': total_issues,
                'open_issues': open_issues,
                'in_progress_issues': in_progress_issues,
                'resolved_issues': resolved_issues
            },
            'recent_issues': [issue.to_dict() for issue in recent_issues]
        })
    
    @app.route('/api/admin/issues', methods=['GET'])
    @limiter.exempt  # Exempt from rate limiting since this is polled frequently by auto-refresh
    def admin_get_issues():
        """Admin view of issues filtered by their district"""
        try:
            # Get JWT token from Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Authorization token required'}), 401
            
            token = auth_header.split(' ')[1]
            
            try:
                # Decode JWT token
                payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                user_id = payload.get('user_id')
                is_admin = payload.get('is_admin')
                
                if not user_id or not is_admin:
                    return jsonify({'error': 'Admin access required'}), 403
                    
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token has expired'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'error': 'Invalid token'}), 401
            
            # Find the admin user
            admin_user = User.query.filter_by(id=user_id, is_admin=True).first()
            if not admin_user:
                return jsonify({'error': 'Admin user not found'}), 404
            
            # Get query parameters
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            status = request.args.get('status')
            category = request.args.get('category')
            
            # Get admin's district
            admin_district = admin_user.district
            
            # Filter issues by admin's district
            query = Issue.query.filter_by(district=admin_district)
            
            if status:
                query = query.filter(Issue.status == status)
            if category:
                query = query.filter(Issue.category == category)
            
            issues = query.order_by(Issue.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            # Convert to dict and add reporter info
            issues_data = []
            for issue in issues.items:
                issue_dict = issue.to_dict()
                # Add reporter info
                reporter = User.query.get(issue.user_id)
                if reporter:
                    issue_dict['reporter_name'] = reporter.username
                    issue_dict['reporter_phone'] = reporter.phone
                    issue_dict['reporter_email'] = reporter.email
                issues_data.append(issue_dict)
            
            return jsonify({
                'issues': issues_data,
                'total': issues.total,
                'pages': issues.pages,
                'current_page': page,
                'admin_district': admin_district
            })
            
        except Exception as e:
            print(f"Admin get issues error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/issues/<int:issue_id>', methods=['GET'])
    def get_issue_details(issue_id):
        """Get detailed information for a specific issue"""
        try:
            # Get JWT token from Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Authorization token required'}), 401
            
            token = auth_header.split(' ')[1]
            
            try:
                # Decode JWT token
                payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                user_id = payload.get('user_id')
                is_admin = payload.get('is_admin')
                
                if not user_id or not is_admin:
                    return jsonify({'error': 'Admin access required'}), 403
                    
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token has expired'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'error': 'Invalid token'}), 401
            
            # Find the admin user
            admin_user = User.query.filter_by(id=user_id, is_admin=True).first()
            if not admin_user:
                return jsonify({'error': 'Admin user not found'}), 404
            
            # Get the issue (ensure it's in admin's district)
            issue = Issue.query.filter_by(id=issue_id, district=admin_user.district).first()
            if not issue:
                return jsonify({'error': 'Issue not found or not in your district'}), 404
            
            # Get reporter information
            reporter = User.query.get(issue.user_id)
            
            # Get status history
            status_history = StatusHistory.query.filter_by(issue_id=issue_id).order_by(StatusHistory.changed_at.desc()).all()
            
            # Get admin comments
            admin_comments = AdminComment.query.filter_by(issue_id=issue_id).order_by(AdminComment.created_at.desc()).all()
            
            # Prepare response
            issue_data = issue.to_dict()
            
            # Add reporter info
            if reporter:
                issue_data['reporter'] = {
                    'name': reporter.username,
                    'email': reporter.email,
                    'phone': reporter.phone
                }
            
            # Add status history
            issue_data['status_history'] = [history.to_dict() for history in status_history]
            
            # Add admin comments
            issue_data['admin_comments'] = [comment.to_dict() for comment in admin_comments]
            
            return jsonify({
                'success': True,
                'issue': issue_data
            })
            
        except Exception as e:
            print(f"Get issue details error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/issues/<int:issue_id>/update', methods=['PUT'])
    def admin_update_issue_with_timeline(issue_id):
        """Update issue status and add admin comment with automatic timeline tracking"""
        try:
            # Get JWT token from Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Authorization token required'}), 401
            
            token = auth_header.split(' ')[1]
            
            try:
                # Decode JWT token
                payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                user_id = payload.get('user_id')
                is_admin = payload.get('is_admin')
                
                if not user_id or not is_admin:
                    return jsonify({'error': 'Admin access required'}), 403
                    
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token has expired'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'error': 'Invalid token'}), 401
            
            # Find the admin user
            admin_user = User.query.filter_by(id=user_id, is_admin=True).first()
            if not admin_user:
                return jsonify({'error': 'Admin user not found'}), 404
            
            # Get request data
            data = request.get_json()
            new_status = data.get('status')
            admin_comment = data.get('comment', '')
            
            if not new_status:
                return jsonify({'error': 'Status is required'}), 400
            
            # Validate status
            valid_statuses = ['open', 'in-progress', 'resolved']
            if new_status not in valid_statuses:
                return jsonify({'error': 'Invalid status'}), 400
            
            # Get the issue (ensure it's in admin's district)
            issue = Issue.query.filter_by(id=issue_id, district=admin_user.district).first()
            if not issue:
                return jsonify({'error': 'Issue not found or not in your district'}), 404
            
            # Store old status for history
            old_status = issue.status
            
            # Update issue status
            issue.status = new_status
            
            # Create status history entry (automatic timeline)
            status_history = StatusHistory(
                issue_id=issue_id,
                old_status=old_status,
                new_status=new_status,
                changed_by=admin_user.username,
                admin_comment=admin_comment if admin_comment else None
            )
            
            # Add admin comment if provided
            if admin_comment:
                comment_entry = AdminComment(
                    issue_id=issue_id,
                    admin_name=admin_user.username,
                    comment=admin_comment
                )
                db.session.add(comment_entry)
            
            # Save all changes
            db.session.add(status_history)
            db.session.commit()

            # Create user-facing notification with friendly message
            try:
                notif_message = None
                if new_status == 'in-progress':
                    notif_message = "Your issue is being worked on and will be solved soon."
                elif new_status == 'resolved':
                    notif_message = "Your issue has been fixed. Thanks for your cooperation."
                else:
                    notif_message = f"Status of your issue '{issue.title}' changed to {new_status}."

                notification = Notification(
                    user_id=issue.user_id,
                    issue_id=issue.id,
                    title="Issue status update",
                    message=notif_message,
                    type="status_update"
                )
                db.session.add(notification)
                db.session.commit()

                # Emit real-time update to the issue reporter if WebSocket is enabled
                if socketio is not None:
                    socketio.emit('status_update', {
                        'issue_id': issue.id,
                        'new_status': new_status,
                        'message': notif_message,
                        'title': issue.title
                    }, room=f"user_{issue.user_id}")
            except Exception as notify_error:
                # Do not break the main flow if notification fails
                print(f"Status update notification error: {notify_error}")
            
            return jsonify({
                'success': True,
                'message': 'Issue updated successfully',
                'issue': {
                    'id': issue.id,
                    'status': issue.status,
                    'updated_by': admin_user.username
                }
            })
            
        except Exception as e:
            print(f"Update issue status error: {e}")
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    # File serving route
    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        """Serve uploaded files"""
        return send_from_directory(upload_dir, filename)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    
    # WebSocket event handlers - DISABLED (Socket.IO disabled for production)
    # @socketio.on('connect')
    # def handle_connect():
    #     """Handle client connection"""
    #     print(f"Client connected: {request.sid}")
    #     emit('connected', {'message': 'Connected to CivicFix real-time updates'})
    # 
    # @socketio.on('disconnect')
    # def handle_disconnect():
    #     """Handle client disconnection"""
    #     print(f"Client disconnected: {request.sid}")
    # 
    # @socketio.on('join_user_room')
    # def handle_join_user_room(data):
    #     """Join user-specific room for notifications"""
    #     try:
    #         user_id = data.get('user_id')
    #         if user_id:
    #             join_room(f"user_{user_id}")
    #             emit('joined_room', {'room': f"user_{user_id}"})
    #             print(f"User {user_id} joined their notification room")
    #     except Exception as e:
    #         print(f"Error joining user room: {e}")
    # 
    # @socketio.on('join_admin_room')
    # def handle_join_admin_room(data):
    #     """Join admin room for admin notifications"""
    #     try:
    #         is_admin = data.get('is_admin', False)
    #         if is_admin:
    #             join_room('admins')
    #             emit('joined_room', {'room': 'admins'})
    #             print("Admin user joined admin room")
    #     except Exception as e:
    #         print(f"Error joining admin room: {e}")
    # 
    # @socketio.on('leave_user_room')
    # def handle_leave_user_room(data):
    #     """Leave user-specific room"""
    #     try:
    #         user_id = data.get('user_id')
    #         if user_id:
    #             leave_room(f"user_{user_id}")
    #             print(f"User {user_id} left their notification room")
    #     except Exception as e:
    #         print(f"Error leaving user room: {e}")
    # 
    # @socketio.on('leave_admin_room')
    # def handle_leave_admin_room():
    #     """Leave admin room"""
    #     try:
    #         leave_room('admins')
    #         print("User left admin room")
    #     except Exception as e:
    #         print(f"Error leaving admin room: {e}")
    
    # Admin Code Request Route
    @app.route('/api/admin/request-code', methods=['POST'])
    def admin_request_code():
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['personal_email', 'official_email', 'full_name', 'province', 'district']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            from models import AdminAuthCode
            from email_service import email_service
            import random
            import string
            from datetime import datetime, timedelta, timezone
            
            # Check if request already exists for this email and district
            existing = AdminAuthCode.query.filter_by(
                personal_email=data.get('personal_email'),
                district=data.get('district')
            ).first()
            
            if existing and existing.is_active and not existing.is_used:
                # Return the existing code instead of error
                return jsonify({
                    'success': True,
                    'message': 'Authorization code already exists for this email and district.',
                    'debug_code': existing.auth_code,  # For development
                    'expires_at': existing.expires_at.isoformat()
                })
            
            # Generate unique authorization code
            def generate_auth_code():
                return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            
            auth_code = generate_auth_code()
            while AdminAuthCode.query.filter_by(auth_code=auth_code).first():
                auth_code = generate_auth_code()
            
            # Create authorization code record
            code_record = AdminAuthCode(
                personal_email=data.get('personal_email'),
                official_email=data.get('official_email'),
                auth_code=auth_code,
                province=data.get('province'),
                district=data.get('district'),
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                created_by=f"System Request - {data.get('full_name')}"
            )
            
            db.session.add(code_record)
            db.session.commit()
            print(f"Authorization code saved to database: {auth_code} for {data.get('personal_email')}")
            
            # Send email with authorization code
            email_sent = email_service.send_admin_authorization_code(
                personal_email=data.get('personal_email'),
                auth_code=auth_code,
                district=data.get('district'),
                province=data.get('province'),
                official_email=data.get('official_email')
            )
            
            if email_sent:
                return jsonify({
                    'success': True,
                    'message': 'Authorization code request submitted successfully. Check your email within 24 hours.',
                    'code_id': code_record.id,
                    'debug_code': auth_code  # For development
                })
            else:
                # If email fails, still return success but log the issue
                print(f"Email failed to send to {data.get('personal_email')}")
                return jsonify({
                    'success': True,
                    'message': 'Request submitted. Email service not configured - using debug code.',
                    'code_id': code_record.id,
                    'debug_code': auth_code,  # For development
                    'expires_at': code_record.expires_at.isoformat()
                })
                
        except Exception as e:
            db.session.rollback()
            print(f"Admin code request error: {e}")
            return jsonify({'error': 'Failed to process request. Please try again.'}), 500

    # Admin Code Reset Route
    @app.route('/api/admin/reset-code', methods=['POST'])
    def admin_reset_code():
        try:
            data = request.get_json()
            from models import AdminAuthCode
            from email_service import email_service
            import random
            import string
            from datetime import datetime, timedelta
            
            # Find existing code record
            existing = AdminAuthCode.query.filter_by(
                personal_email=data.get('personal_email'),
                official_email=data.get('official_email')
            ).first()
            
            if not existing:
                return jsonify({'error': 'No authorization code found for these email addresses.'}), 404
            
            # Generate new authorization code
            def generate_auth_code():
                return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            
            new_auth_code = generate_auth_code()
            while AdminAuthCode.query.filter_by(auth_code=new_auth_code).first():
                new_auth_code = generate_auth_code()
            
            # Update existing record
            existing.auth_code = new_auth_code
            existing.is_used = False
            existing.is_active = True
            existing.expires_at = datetime.utcnow() + timedelta(days=7)
            existing.created_at = datetime.utcnow()
            
            db.session.commit()
            
            # Send email with new authorization code
            email_sent = email_service.send_code_reset_notification(
                personal_email=data.get('personal_email'),
                new_auth_code=new_auth_code,
                district=existing.district,
                province=existing.province
            )
            
            if email_sent:
                return jsonify({
                    'message': 'Authorization code reset successfully. Check your email for the new code.'
                })
            else:
                print(f"Reset email failed to send to {data.get('personal_email')}")
                return jsonify({
                    'message': 'Code reset completed. If email is configured, you will receive the new code.',
                    'debug_code': new_auth_code  # Remove this in production
                })
                
        except Exception as e:
            db.session.rollback()
            print(f"Admin code reset error: {e}")
            return jsonify({'error': 'Failed to reset code. Please try again.'}), 500

    # Admin Registration Route (Updated for new email system)
    @app.route('/api/admin/register', methods=['POST'])
    def admin_register():
        try:
            data = request.get_json()
            print(f"Admin registration data received: {data}")
            
            # Validate required fields
            required_fields = ['email', 'password', 'full_name', 'province', 'district', 'phone']
            missing_fields = []
            for field in required_fields:
                if not data.get(field):
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"Missing fields: {missing_fields}")
                return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
            
            # Check if admin user already exists
            existing_user = User.query.filter_by(email=data['email']).first()
            if existing_user:
                print(f"Admin user already exists: {existing_user.email}")
                return jsonify({
                    'message': 'Admin already registered. You can now login.',
                    'user_id': existing_user.id
                })
            
            # Hash the password using bcrypt
            print(f"Creating admin user: {data['email']}")
            password_bytes = data['password'].encode('utf-8')
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(password_bytes, salt)
            
            # Create admin user in our database
            admin_user = User(
                id=str(uuid.uuid4()),  # Generate new UUID
                username=data['full_name'],  # Use the full name provided by admin
                email=data['email'],
                password_hash=password_hash.decode('utf-8'),  # Store as string
                is_admin=True,
                is_district_admin=True,
                province=data.get('province'),
                district=data.get('district'),
                phone=data.get('phone')
            )
            db.session.add(admin_user)
            db.session.commit()
            
            print(f"Admin user created successfully: {admin_user.email}")
            return jsonify({
                'message': 'Admin registered successfully',
                'user_id': admin_user.id
            })
                
        except Exception as e:
            db.session.rollback()
            print(f"Admin registration error: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500

    # Debug: Fix admin user permissions
    @app.route('/api/admin/fix-user-permissions', methods=['POST'])
    def fix_admin_user_permissions():
        try:
            # Find the existing user
            existing_user = User.query.filter_by(id='6c8f0e2a-3a98-4a6b-a85d-a4eba04b3982').first()
            
            if not existing_user:
                return jsonify({'error': 'User not found'}), 404
            
            # Update the user to have admin permissions
            existing_user.is_admin = True
            existing_user.is_district_admin = True
            existing_user.province = 'Kigali'
            existing_user.district = 'Kicukiro'
            existing_user.phone = '0795903950'
            
            db.session.commit()
            
            print(f"Updated admin permissions for user: {existing_user.email}")
            return jsonify({
                'message': 'Admin permissions updated successfully', 
                'user_id': existing_user.id,
                'is_admin': existing_user.is_admin,
                'is_district_admin': existing_user.is_district_admin
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating admin permissions: {e}")
            return jsonify({'error': str(e)}), 500

    # Admin Login Route
    @app.route('/api/admin/login', methods=['POST'])
    def admin_login():
        try:
            data = request.get_json()
            print(f"Admin login attempt: {data}")
            
            # Validate required fields
            if not data.get('email') or not data.get('password'):
                return jsonify({'error': 'Email and password are required'}), 400
            
            # Find admin user in our database
            print(f"Looking for admin user: {data['email']}")
            user = User.query.filter_by(email=data['email'], is_admin=True).first()
            
            if not user:
                print(f"No admin user found with email: {data['email']}")
                return jsonify({'error': 'Invalid credentials'}), 401
            
            if not user.password_hash:
                print(f"Admin user found but no password hash set: {user.email}")
                return jsonify({'error': 'Account not properly configured. Please contact support.'}), 401
            
            # Verify password using bcrypt
            print(f"Verifying password for user: {user.email}")
            password_bytes = data['password'].encode('utf-8')
            stored_hash = user.password_hash.encode('utf-8')
            
            if bcrypt.checkpw(password_bytes, stored_hash):
                print(f"Password verification successful for: {user.email}")
                
                # Generate JWT token
                payload = {
                    'user_id': str(user.id),
                    'email': user.email,
                    'is_admin': user.is_admin,
                    'is_district_admin': user.is_district_admin,
                    'district': user.district,
                    'exp': datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours
                }
                
                token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
                print(f"JWT token generated for: {user.email}")
                
                return jsonify({
                    'message': 'Login successful',
                    'token': token,
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'username': user.username,
                        'province': user.province,
                        'district': user.district,
                        'is_district_admin': user.is_district_admin
                    }
                })
            else:
                print(f"Password verification failed for: {user.email}")
                return jsonify({'error': 'Invalid credentials'}), 401
                
        except Exception as e:
            print(f"Admin login error: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500


    # Admin Update Issue Status
    @app.route('/api/admin/issues/<int:issue_id>/status', methods=['PUT'])
    @token_required
    def admin_update_issue_status(issue_id):
        if not request.current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        try:
            data = request.get_json()
            new_status = data.get('status')
            
            if new_status not in ['open', 'in-progress', 'resolved']:
                return jsonify({'error': 'Invalid status'}), 400
            
            issue = Issue.query.get_or_404(issue_id)
            old_status = issue.status
            issue.status = new_status
            db.session.commit()
            
            # Send real-time notification to all users
            # Socket.IO disabled - real-time notifications skipped
            # socketio.emit('new_issue', {
            #     'issue_id': issue.id,
            #     'title': issue.title,
            #     'category': issue.category,
            #     'location': issue.location_address or 'Location provided',
            #     'message': f"New {issue.category} issue reported: {issue.title}"
            # })
            # 
            # # Send special notification to admins
            # socketio.emit('admin_new_issue', {
            #     'issue_id': issue.id,
            #     'title': issue.title,
            #     'category': issue.category,
            #     'location': issue.location_address or 'Location provided',
            #     'description': issue.description,
            #     'reporter_email': request.current_user.email,
            #     'message': f"ADMIN ALERT: New {issue.category} issue requires attention",
            #     'priority': 'high' if issue.category in ['Emergency', 'Safety'] else 'normal'
            # }, room='admins')
            
            # Send notification to issue reporter
            notification = Notification(
                user_id=issue.user_id,
                message=f"Your reported issue '{issue.title}' status has been updated to {new_status}",
                type="status_update"
            )
            db.session.add(notification)
            db.session.commit()
            
            return jsonify({
                'message': 'Status updated successfully',
                'issue_id': issue_id,
                'new_status': new_status
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    # Admin Profile Update Route
    @app.route('/api/admin/profile', methods=['PUT'])
    def update_admin_profile():
        try:
            data = request.get_json()
            
            # Get JWT token from Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Authorization token required'}), 401
            
            token = auth_header.split(' ')[1]
            
            try:
                # Decode JWT token
                payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                user_id = payload.get('user_id')
                
                if not user_id:
                    return jsonify({'error': 'Invalid token'}), 401
                    
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token has expired'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'error': 'Invalid token'}), 401
            
            # Find the admin user
            user = User.query.filter_by(id=user_id, is_admin=True).first()
            if not user:
                return jsonify({'error': 'Admin user not found'}), 404
            
            # Update allowed fields
            if 'full_name' in data:
                # Store full name in username field for now
                user.username = data['full_name']
            
            if 'phone' in data:
                user.phone = data['phone']
            
            db.session.commit()
            
            return jsonify({
                'message': 'Profile updated successfully',
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'username': user.username,
                    'phone': user.phone,
                    'district': user.district
                }
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"Profile update error: {e}")
            return jsonify({'error': str(e)}), 500
    
    # Register catch-all route LAST using add_url_rule to ensure it has lowest priority
    def serve_static(filename):
        """Serve static files (HTML, CSS, JS) and SPA routing"""
        try:
            return send_from_directory(app.static_folder, filename)
        except:
            # If file not found, serve index.html for SPA routing
            try:
                return send_from_directory(app.static_folder, 'index.html')
            except:
                return '', 404
    
    app.add_url_rule('/<path:filename>', 'serve_static', serve_static, methods=['GET'])
    
    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    
    print("Starting CivicFix Server (Flask + SocketIO)")
    print("Server: http://localhost:5000")
    print("Admin: http://localhost:5500/admin-request-code.html")
    
    # Run a single combined HTTP + WebSocket server on port 5000
    # Check for WERKZUEG_RUN_MAIN to prevent the reloader from initializing SocketIO twice
    if app.config['DEBUG'] and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        print("Running in debug mode with reloader - SocketIO will attach later.")
    else:
        socketio.run(
            app,
            debug=app.config['DEBUG'],
            host='127.0.0.1',
            port=5000
        )
