"""
Email Notification System for BTFD
Sends daily trading signal reports via email
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
import os
from typing import List, Dict, Optional
from datetime import date

from ..config.settings import get_config, EmailConfig

class EmailSender:
    """Email notification sender"""
    
    def __init__( self ):
        self.config = get_config();
        self.smtp_config = self._load_email_config();
    
    def _load_email_config( self ) -> Dict[str, str]:
        """Load email configuration from database"""
        
        try:
            conn = self.config.get_database_connection();
            cursor = conn.cursor();
            
            cursor.execute( "SELECT smtp_server, smtp_port, username, password, recipients, enabled FROM email_config WHERE enabled = 1 LIMIT 1" );
            result = cursor.fetchone();
            conn.close();
            
            if result:
                return {
                    'smtp_server': result[0],
                    'smtp_port': result[1], 
                    'username': result[2],
                    'password': result[3],
                    'recipients': result[4],
                    'enabled': bool( result[5] )
                };
            else:
                print( "ℹ️  No email configuration found in database" );
                return {};
                
        except Exception as e:
            print( f"⚠️  Error loading email configuration: {e}" );
            return {};
    
    def setup_email_config( self, smtp_server: str, smtp_port: int, username: str, 
                          password: str, recipients: str ):
        """
        Setup email configuration in database
        
        Args:
            smtp_server: SMTP server address (e.g. 'smtp.gmail.com')
            smtp_port: SMTP port (usually 587)
            username: Email username
            password: Email password or app password
            recipients: Comma-separated list of recipient emails
        """
        
        try:
            conn = self.config.get_database_connection();
            cursor = conn.cursor();
            
            cursor.execute(
                """INSERT OR REPLACE INTO email_config 
                   (config_id, smtp_server, smtp_port, username, password, recipients, enabled)
                   VALUES (1, ?, ?, ?, ?, ?, 1)""",
                ( smtp_server, smtp_port, username, password, recipients )
            );
            
            conn.commit();
            conn.close();
            
            print( f"✅ Email configuration saved" );
            self.smtp_config = self._load_email_config();
            
        except Exception as e:
            print( f"❌ Error saving email configuration: {e}" );
    
    def send_daily_signals( self, signals: List[Dict], html_content: str, chart_paths: Dict[str, str] = None ) -> bool:
        """
        Send daily signals via email with embedded charts
        
        Args:
            signals: List of signal dictionaries
            html_content: HTML formatted email content
            chart_paths: Dictionary mapping symbol to chart file path
            
        Returns:
            True if sent successfully, False otherwise
        """
        
        if not self.smtp_config or not self.smtp_config.get( 'enabled' ):
            print( "⚠️  Email not configured or disabled" );
            return False;
        
        try:
            # Create message with mixed content for images
            message = MIMEMultipart( "related" );
            message["Subject"] = f"🎯 BTFD Daily Signals - {date.today()} ({len( signals )} signals)";
            message["From"] = self.smtp_config['username'];
            message["To"] = self.smtp_config['recipients'];
            
            # Create alternative container for text/html
            msg_alternative = MIMEMultipart( "alternative" );
            
            # HTML content already contains inline image references
            updated_html_content = html_content;
            
            # Create HTML part
            html_part = MIMEText( updated_html_content, "html" );
            msg_alternative.attach( html_part );
            
            # Attach the alternative container
            message.attach( msg_alternative );
            
            # Embed chart images
            if chart_paths:
                for symbol, chart_path in chart_paths.items():
                    if os.path.exists( chart_path ):
                        print( f"📎 Embedding chart for {symbol}: {os.path.basename( chart_path )}" );
                        with open( chart_path, 'rb' ) as f:
                            img_data = f.read();
                        
                        # Create image attachment
                        img = MIMEImage( img_data );
                        img.add_header( 'Content-ID', f'<{symbol}_chart>' );
                        img.add_header( 'Content-Disposition', f'inline; filename="{os.path.basename( chart_path )}"' );
                        message.attach( img );
            
            # Connect to server and send
            context = ssl.create_default_context();
            
            with smtplib.SMTP( self.smtp_config['smtp_server'], self.smtp_config['smtp_port'] ) as server:
                server.starttls( context=context );
                server.login( self.smtp_config['username'], self.smtp_config['password'] );
                
                recipients = [email.strip() for email in self.smtp_config['recipients'].split( ',' )];
                server.sendmail( self.smtp_config['username'], recipients, message.as_string() );
            
            print( f"✅ Email sent successfully to {len( recipients )} recipient(s)" );
            return True;
            
        except Exception as e:
            print( f"❌ Error sending email: {e}" );
            return False;
    
    def send_test_email( self ) -> bool:
        """Send a test email to verify configuration"""
        
        if not self.smtp_config or not self.smtp_config.get( 'enabled' ):
            print( "⚠️  Email not configured" );
            return False;
        
        test_html = f"""
        <h2>🧪 BTFD Email Test</h2>
        <p>This is a test email from the BTFD Daily Scanner system.</p>
        <p><strong>Configuration:</strong></p>
        <ul>
            <li>SMTP Server: {self.smtp_config['smtp_server']}</li>
            <li>Port: {self.smtp_config['smtp_port']}</li>
            <li>Username: {self.smtp_config['username']}</li>
        </ul>
        <p>If you receive this email, your BTFD email configuration is working correctly!</p>
        <p><em>Sent at {date.today()}</em></p>
        """;
        
        return self.send_daily_signals( [], test_html );
    
    def is_configured( self ) -> bool:
        """Check if email is properly configured"""
        return bool( self.smtp_config and self.smtp_config.get( 'enabled' ) );

# Convenience functions for common email providers
def setup_gmail( username: str, password: str, recipients: str ) -> EmailSender:
    """Setup Gmail SMTP configuration"""
    
    sender = EmailSender();
    sender.setup_email_config(
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        username=username,
        password=password,  # Use App Password for Gmail
        recipients=recipients
    );
    return sender;

def setup_outlook( username: str, password: str, recipients: str ) -> EmailSender:
    """Setup Outlook/Hotmail SMTP configuration"""
    
    sender = EmailSender();
    sender.setup_email_config(
        smtp_server="smtp-mail.outlook.com",
        smtp_port=587,
        username=username,
        password=password,
        recipients=recipients
    );
    return sender;