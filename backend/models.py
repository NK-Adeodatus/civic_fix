from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    """Extended user model that links to Supabase Auth users"""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True)  # Supabase Auth user ID
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # For admin users (bcrypt hash)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Location fields for all users
    province = db.Column(db.String(50), nullable=True)
    district = db.Column(db.String(50), nullable=True)
    sector = db.Column(db.String(50), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    
    # Admin-specific fields (district is used for admin jurisdiction)
    is_district_admin = db.Column(db.Boolean, default=False)
    
    # Email verification fields
    is_email_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(6), nullable=True)
    verification_code_expires = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    issues = db.relationship('Issue', backref='reporter', lazy=True)
    votes = db.relationship('Vote', backref='voter', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'province': self.province,
            'district': self.district,
            'sector': self.sector,
            'phone': self.phone,
            'is_district_admin': self.is_district_admin,
            'created_at': self.created_at.isoformat()
        }

class Issue(db.Model):
    """Issue reports from citizens"""
    __tablename__ = 'issues'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='Open', nullable=False)
    
    # Location fields (multi-method system)
    street_address = db.Column(db.String(200))
    landmark_reference = db.Column(db.String(200))
    detailed_description = db.Column(db.Text)
    
    # Administrative location fields
    province = db.Column(db.String(50))
    district = db.Column(db.String(50))
    sector = db.Column(db.String(50))
    
    # Image and metadata
    image_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    votes = db.relationship('Vote', backref='issue', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='issue', lazy=True, cascade='all, delete-orphan')
    status_history = db.relationship('StatusHistory', backref='issue', lazy=True, cascade='all, delete-orphan')
    admin_comments = db.relationship('AdminComment', backref='issue', lazy=True, cascade='all, delete-orphan')
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_status', 'status'),
        db.Index('idx_category', 'category'),
        db.Index('idx_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f'<Issue {self.title}>'
    
    @property
    def vote_count(self):
        return len(self.votes)
    
    def to_dict(self, include_votes=True):
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'status': self.status,
            'street_address': self.street_address,
            'landmark_reference': self.landmark_reference,
            'detailed_description': self.detailed_description,
            'province': self.province,
            'district': self.district,
            'sector': self.sector,
            'image_url': self.image_url,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'user_id': self.user_id,
            'reporter_username': self.reporter.username if self.reporter else None
        }
        if include_votes:
            data['vote_count'] = self.vote_count
        return data

class Vote(db.Model):
    """Citizen votes on issues"""
    __tablename__ = 'votes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    issue_id = db.Column(db.Integer, db.ForeignKey('issues.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate votes
    __table_args__ = (
        db.UniqueConstraint('user_id', 'issue_id', name='unique_user_issue_vote'),
    )
    
    def __repr__(self):
        return f'<Vote {self.user_id} -> {self.issue_id}>'

class Notification(db.Model):
    """User notifications"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    issue_id = db.Column(db.Integer, db.ForeignKey('issues.id'), nullable=True)  # Optional link to issue
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='info')  # info, success, warning, error
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'read': self.read,
            'issue_id': self.issue_id,
            'created_at': self.created_at.isoformat()
        }

class AdminAuthCode(db.Model):
    """Admin authorization codes for district-based access"""
    __tablename__ = 'admin_auth_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    personal_email = db.Column(db.String(120), unique=True, nullable=False)  # Admin's real email
    official_email = db.Column(db.String(120), nullable=False)  # Government email for the system
    auth_code = db.Column(db.String(20), unique=True, nullable=False)
    province = db.Column(db.String(50), nullable=False)
    district = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_used = db.Column(db.Boolean, default=False)  # Has this code been used to register?
    expires_at = db.Column(db.DateTime, nullable=True)  # Code expiration
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(120), nullable=True)  # Who created this code
    
    def to_dict(self):
        return {
            'id': self.id,
            'personal_email': self.personal_email,
            'official_email': self.official_email,
            'auth_code': self.auth_code,
            'province': self.province,
            'district': self.district,
            'is_active': self.is_active,
            'is_used': self.is_used,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat()
        }

class StatusHistory(db.Model):
    """Track status changes for issues with automatic timeline"""
    __tablename__ = 'status_history'
    
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issues.id'), nullable=False)
    old_status = db.Column(db.String(50), nullable=True)  # Previous status (null for creation)
    new_status = db.Column(db.String(50), nullable=False)  # New status
    changed_by = db.Column(db.String(100), nullable=False)  # Admin name who made the change
    admin_comment = db.Column(db.Text, nullable=True)  # Admin's explanation of the action
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'issue_id': self.issue_id,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'changed_by': self.changed_by,
            'admin_comment': self.admin_comment,
            'changed_at': self.changed_at.isoformat()
        }

class AdminComment(db.Model):
    """Admin comments and notes on issues"""
    __tablename__ = 'admin_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issues.id'), nullable=False)
    admin_name = db.Column(db.String(100), nullable=False)  # Name of admin who made comment
    comment = db.Column(db.Text, nullable=False)  # The actual comment/note
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'issue_id': self.issue_id,
            'admin_name': self.admin_name,
            'comment': self.comment,
            'created_at': self.created_at.isoformat()
        }
