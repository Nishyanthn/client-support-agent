import smtplib
import secrets
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from native_functions import db

# Configure email settings
SMTP_SERVER = "smtp.gmail.com"  # or your email provider
SMTP_PORT = 587
SENDER_EMAIL = "support@inextlabs.com"  # Your email
SENDER_PASSWORD = "your_app_password"  # Use app-specific password
RESET_URL_BASE = "https://yourdomain.com/reset-password"  # Your frontend URL

# Create users collection for password reset tokens
users_collection = db.users

@kernel_function(
    description="Initiates a password reset process for a user by sending a real email with a secure reset link.",
    name="request_password_reset"
)
def request_password_reset(email: str) -> str:
    """
    Real implementation of password reset with email sending.
    
    Process:
    1. Validate email format
    2. Check if user exists
    3. Generate secure token
    4. Store token with expiry
    5. Send email with reset link
    6. Return success/error message
    """
    print(f"🤖 Action: Running 'request_password_reset' for email: {email}")
    
    # Step 1: Validate email format
    if not email or "@" not in email or "." not in email:
        print(f"Invalid email format: {email}")
        return "Invalid email address format. Please provide a valid email."
    
    try:
        # Step 2: Check if user exists
        user = users_collection.find_one({"email": email})
        
        if not user:
            # Security: Don't reveal if email exists or not (prevents email enumeration)
            print(f"User with email {email} not found, but returning success message")
            return f"If an account exists with {email}, a password reset link has been sent. Please check your inbox."
        
        # Step 3: Generate secure token (32 bytes = 64 hex characters)
        reset_token = secrets.token_urlsafe(32)
        
        # Hash token for storage (never store plain tokens)
        token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
        
        # Step 4: Store token with 1-hour expiry
        expiry_time = datetime.utcnow() + timedelta(hours=1)
        
        users_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "reset_token_hash": token_hash,
                    "reset_token_expiry": expiry_time,
                    "reset_requested_at": datetime.utcnow()
                }
            }
        )
        
        print(f"Token generated and stored for {email}")
        
        # Step 5: Send email
        reset_link = f"{RESET_URL_BASE}?token={reset_token}&email={email}"
        
        email_sent = send_reset_email(
            to_email=email,
            reset_link=reset_link,
            user_name=user.get("name", "User")
        )
        
        if email_sent:
            print(f"✅ Password reset email sent to {email}")
            return f"A password reset link has been successfully sent to {email}. The link will expire in 1 hour. Please check your inbox and spam folder."
        else:
            print(f"❌ Failed to send email to {email}")
            return "We encountered an error sending the reset email. Please try again later or contact support."
            
    except Exception as e:
        print(f"❌ Error in password reset: {e}")
        return "An error occurred while processing your password reset request. Please try again later."


def send_reset_email(to_email: str, reset_link: str, user_name: str) -> bool:
    """
    Sends the actual password reset email using SMTP.
    
    Args:
        to_email: Recipient email address
        reset_link: Complete reset URL with token
        user_name: User's name for personalization
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = "Password Reset Request - InextLabs Support"
        message["From"] = f"InextLabs Support <{SENDER_EMAIL}>"
        message["To"] = to_email
        
        # Plain text version
        text = f"""
Hello {user_name},

We received a request to reset your password for your InextLabs account.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour for security reasons.

If you didn't request this password reset, please ignore this email or contact our support team if you have concerns.

Best regards,
InextLabs Support Team
support@inextlabs.com
        """
        
        # HTML version (better looking)
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #FF6B35 0%, #E5522E 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
        }}
        .content {{
            background: #f9f9f9;
            padding: 30px;
            border-radius: 0 0 10px 10px;
        }}
        .button {{
            display: inline-block;
            padding: 15px 30px;
            background: linear-gradient(135deg, #FF6B35 0%, #FF8C61 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            margin: 20px 0;
            font-weight: bold;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            font-size: 12px;
            color: #666;
        }}
        .warning {{
            background: #FFF5F2;
            border-left: 4px solid #FF6B35;
            padding: 15px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset Request</h1>
        </div>
        <div class="content">
            <p>Hello {user_name},</p>
            
            <p>We received a request to reset your password for your InextLabs account.</p>
            
            <p>Click the button below to reset your password:</p>
            
            <center>
                <a href="{reset_link}" class="button">Reset My Password</a>
            </center>
            
            <div class="warning">
                <strong>⏰ Important:</strong> This link will expire in 1 hour for security reasons.
            </div>
            
            <p>If the button doesn't work, copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #FF6B35;">{reset_link}</p>
            
            <p>If you didn't request this password reset, please ignore this email or contact our support team if you have concerns.</p>
            
            <p>Best regards,<br>
            <strong>InextLabs Support Team</strong></p>
        </div>
        <div class="footer">
            <p>This is an automated email. Please do not reply.</p>
            <p>Need help? Contact us at support@inextlabs.com</p>
        </div>
    </div>
</body>
</html>
        """
        
        # Attach both versions
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        message.attach(part1)
        message.attach(part2)
        
        # Send email via SMTP
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(message)
        
        return True
        
    except smtplib.SMTPException as e:
        print(f"SMTP Error: {e}")
        return False
    except Exception as e:
        print(f"Email Error: {e}")
        return False


# New function to verify and reset password
@kernel_function(
    description="Verifies a password reset token and updates the user's password.",
    name="verify_and_reset_password"
)
def verify_and_reset_password(token: str, email: str, new_password: str) -> str:
    """
    Verifies the reset token and updates the password.
    
    This would be called from your frontend reset password page.
    """
    try:
        # Hash the provided token
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Find user with matching token and email
        user = users_collection.find_one({
            "email": email,
            "reset_token_hash": token_hash
        })
        
        if not user:
            return "Invalid or expired reset link. Please request a new password reset."
        
        # Check if token is expired
        if user.get("reset_token_expiry") < datetime.utcnow():
            return "This reset link has expired. Please request a new password reset."
        
        # Validate new password (add your password requirements)
        if len(new_password) < 8:
            return "Password must be at least 8 characters long."
        
        # Hash new password (use bcrypt in production!)
        import hashlib
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        
        # Update password and clear reset token
        users_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "password_hash": password_hash,
                    "password_updated_at": datetime.utcnow()
                },
                "$unset": {
                    "reset_token_hash": "",
                    "reset_token_expiry": ""
                }
            }
        )
        
        print(f"✅ Password successfully reset for {email}")
        return "Your password has been successfully reset. You can now log in with your new password."
        
    except Exception as e:
        print(f"❌ Error verifying reset token: {e}")
        return "An error occurred while resetting your password. Please try again."


# Alternative: Use SendGrid (easier, more reliable)
def send_reset_email_sendgrid(to_email: str, reset_link: str, user_name: str) -> bool:
    """
    Alternative implementation using SendGrid API (recommended for production)
    
    Setup:
    1. pip install sendgrid
    2. Get API key from sendgrid.com
    3. Set SENDGRID_API_KEY in environment
    """
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        import os
        
        message = Mail(
            from_email='support@inextlabs.com',
            to_emails=to_email,
            subject='Password Reset Request - InextLabs Support',
            html_content=f"""
                <!-- Same HTML as above -->
                <h1>Hello {user_name}</h1>
                <p>Click here to reset: <a href="{reset_link}">Reset Password</a></p>
            """
        )
        
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        
        return response.status_code == 202
        
    except Exception as e:
        print(f"SendGrid Error: {e}")
        return False