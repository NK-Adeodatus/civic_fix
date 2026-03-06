"""
Email service for CivicFix admin authorization codes
Handles sending authorization codes and password reset emails
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

class EmailService:
    def __init__(self):
        # Email configuration (you can use Gmail, SendGrid, or any SMTP service)
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.email_user = os.environ.get('EMAIL_USER', 'your-app-email@gmail.com')
        self.email_password = os.environ.get('EMAIL_PASSWORD', 'your-app-password')
        self.from_name = "CivicFix Rwanda"
    
    def send_email(self, to_email, subject, html_content, text_content=None):
        """Send an email with HTML content"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.email_user}>"
            msg['To'] = to_email
            
            # Add text version if provided
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            # Add HTML version
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Email sending failed: {e}")
            return False
    
    def send_admin_authorization_code(self, personal_email, auth_code, district, province, official_email):
        """Send authorization code to admin's personal email"""
        
        subject = f"CivicFix Admin Authorization Code - {district} District"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .auth-code {{ background: #fff; border: 2px solid #667eea; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0; }}
                .code {{ font-size: 24px; font-weight: bold; color: #667eea; letter-spacing: 3px; }}
                .info-box {{ background: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; margin: 20px 0; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>CivicFix Rwanda</h1>
                    <h2>Admin Authorization Code</h2>
                </div>
                
                <div class="content">
                    <p>Dear District Administrator,</p>
                    
                    <p>You have been granted administrative access to CivicFix for <strong>{district} District, {province}</strong>.</p>
                    
                    <div class="auth-code">
                        <p><strong>Your Authorization Code:</strong></p>
                        <div class="code">{auth_code}</div>
                    </div>
                    
                    <div class="info-box">
                        <h3>Registration Instructions:</h3>
                        <ol>
                            <li>Go to the CivicFix admin registration page</li>
                            <li>Use this email as your <strong>Official Email</strong>: <code>{official_email}</code></li>
                            <li>Enter your authorization code: <code>{auth_code}</code></li>
                            <li>Select <strong>{province}</strong> as your province</li>
                            <li>Select <strong>{district}</strong> as your district</li>
                            <li>Complete the registration process</li>
                        </ol>
                    </div>
                    
                    <div class="warning">
                        <h3>Important Security Notes:</h3>
                        <ul>
                            <li>This code is valid for <strong>7 days</strong> from the date of this email</li>
                            <li>Keep this code confidential - do not share it with anyone</li>
                            <li>You can only use this code once to register</li>
                            <li>If you lose this code, contact your IT administrator for a new one</li>
                        </ul>
                    </div>
                    
                    <p><strong>Your Jurisdiction:</strong> You will have administrative access to manage infrastructure issues reported from {district} District only.</p>
                    
                    <p>If you have any questions or need assistance, please contact your IT administrator.</p>
                    
                    <p>Best regards,<br>
                    <strong>CivicFix Rwanda Team</strong></p>
                </div>
                
                <div class="footer">
                    <p>This is an automated message from CivicFix Rwanda. Please do not reply to this email.</p>
                    <p>© 2024 CivicFix Rwanda - Infrastructure Issue Management System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        CivicFix Rwanda - Admin Authorization Code
        
        Dear District Administrator,
        
        You have been granted administrative access to CivicFix for {district} District, {province}.
        
        Your Authorization Code: {auth_code}
        
        Registration Instructions:
        1. Go to the CivicFix admin registration page
        2. Use this email as your Official Email: {official_email}
        3. Enter your authorization code: {auth_code}
        4. Select {province} as your province
        5. Select {district} as your district
        6. Complete the registration process
        
        Important:
        - This code is valid for 7 days
        - Keep it confidential
        - You can only use it once
        - Contact IT if you lose it
        
        Best regards,
        CivicFix Rwanda Team
        """
        
        return self.send_email(personal_email, subject, html_content, text_content)
    
    def send_code_reset_notification(self, personal_email, new_auth_code, district, province):
        """Send new authorization code when admin requests reset"""
        
        subject = f"CivicFix Authorization Code Reset - {district} District"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .auth-code {{ background: #fff; border: 2px solid #f39c12; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0; }}
                .code {{ font-size: 24px; font-weight: bold; color: #f39c12; letter-spacing: 3px; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Authorization Code Reset</h1>
                    <h2>CivicFix Rwanda</h2>
                </div>
                
                <div class="content">
                    <p>Dear District Administrator,</p>
                    
                    <p>Your authorization code for <strong>{district} District, {province}</strong> has been reset as requested.</p>
                    
                    <div class="auth-code">
                        <p><strong>Your New Authorization Code:</strong></p>
                        <div class="code">{new_auth_code}</div>
                    </div>
                    
                    <div class="warning">
                        <h3>Security Notice:</h3>
                        <ul>
                            <li>Your previous authorization code is now invalid</li>
                            <li>This new code is valid for <strong>7 days</strong></li>
                            <li>If you did not request this reset, contact IT immediately</li>
                        </ul>
                    </div>
                    
                    <p>You can now use this new code to complete your admin registration.</p>
                    
                    <p>Best regards,<br>
                    <strong>CivicFix Rwanda Team</strong></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(personal_email, subject, html_content)

# Global email service instance
email_service = EmailService()
