import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    FRONTEND_ORIGIN = os.environ.get('FRONTEND_ORIGIN') or 'http://localhost:5500'
    
    # Database configuration
    # Use Supabase PostgreSQL as primary database
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # If DATABASE_URL is not set, construct it from Supabase URL
    if not DATABASE_URL and os.environ.get('SUPABASE_URL'):
        # Extract database connection from Supabase URL
        supabase_url = os.environ.get('SUPABASE_URL')
        # Convert https://xxx.supabase.co to postgresql://postgres:[password]@db.xxx.supabase.co:5432/postgres
        if 'supabase.co' in supabase_url:
            project_ref = supabase_url.split('//')[1].split('.')[0]
            db_password = os.environ.get('SUPABASE_DB_PASSWORD', 'your_db_password')
            DATABASE_URL = f"postgresql://postgres:{db_password}@db.{project_ref}.supabase.co:5432/postgres"
    
    # Fallback to SQLite for development if no Supabase config
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///civicfix.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload settings
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = "memory://"
    
    @staticmethod
    def init_app(app):
        pass
