"""
MOTD (Message of the Day) Writer for BTFD
Writes daily trading signals to system MOTD or user MOTD file
"""

import os
import stat
from pathlib import Path
from typing import List, Dict
from datetime import datetime

class MOTDWriter:
    """MOTD message writer"""
    
    def __init__( self ):
        self.system_motd = Path( "/etc/motd" );
        self.user_motd = Path.home() / ".motd";
        self.btfd_motd = Path.home() / ".btfd_motd";
    
    def write_signals_to_motd( self, signals_text: str ) -> bool:
        """
        Write signals to user MOTD (~/.motd) with bashrc integration for reliable display
        
        Args:
            signals_text: Formatted signals text for MOTD
            
        Returns:
            True if written successfully, False otherwise
        """
        
        # Primary: Write to user MOTD file
        if self._write_user_motd( signals_text ):
            # Ensure bashrc integration is set up
            self._ensure_bashrc_integration();
            print( f"✅ MOTD updated with signals in {self.user_motd}" );
            return True;
        
        # Fallback: Try system MOTD with sudo if needed
        print( "⚠️  User MOTD failed, trying system MOTD as fallback..." );
        if self._write_system_motd_with_sudo( signals_text ):
            print( "✅ MOTD updated with signals in /etc/motd" );
            return True;
        
        print( "❌ Failed to update both user and system MOTD" );
        return False;
    
    def _write_system_motd_with_sudo( self, signals_text: str ) -> bool:
        """
        Write to system MOTD using sudo if necessary
        
        Args:
            signals_text: Formatted signals text
            
        Returns:
            True if written successfully, False otherwise
        """
        
        import subprocess
        import tempfile
        
        try:
            # First try direct write (if we have permissions)
            if self._try_write_system_motd( signals_text ):
                return True;
            
            # If direct write fails, try with sudo
            print( "⚠️  Need elevated permissions for /etc/motd, trying sudo..." );
            
            # Read existing MOTD content
            existing_content = "";
            try:
                with open( self.system_motd, 'r' ) as f:
                    existing_content = f.read();
            except (PermissionError, FileNotFoundError):
                # If we can't read, assume empty
                pass;
            
            # Remove existing BTFD section and add new one
            cleaned_content = self._remove_btfd_section( existing_content );
            new_content = cleaned_content.rstrip() + "\n\n" + self._wrap_btfd_section( signals_text ) + "\n";
            
            # Write to temporary file
            with tempfile.NamedTemporaryFile( mode='w', delete=False ) as temp_file:
                temp_file.write( new_content );
                temp_path = temp_file.name;
            
            # Use sudo to copy temp file to /etc/motd
            result = subprocess.run(
                ['sudo', 'cp', temp_path, '/etc/motd'],
                capture_output=True,
                text=True
            );
            
            # Clean up temp file
            os.unlink( temp_path );
            
            if result.returncode == 0:
                return True;
            else:
                print( f"❌ sudo cp failed: {result.stderr}" );
                return False;
                
        except Exception as e:
            print( f"❌ Error writing to system MOTD: {e}" );
            return False;
    
    def _try_write_system_motd( self, signals_text: str ) -> bool:
        """Try to write to system MOTD (/etc/motd)"""
        
        try:
            # Check if we have write permission
            if not os.access( str( self.system_motd.parent ), os.W_OK ):
                return False;
            
            # Read existing MOTD content
            existing_content = "";
            if self.system_motd.exists():
                with open( self.system_motd, 'r' ) as f:
                    existing_content = f.read();
            
            # Remove any existing BTFD section
            cleaned_content = self._remove_btfd_section( existing_content );
            
            # Add new BTFD section
            new_content = cleaned_content.rstrip() + "\n\n" + self._wrap_btfd_section( signals_text ) + "\n";
            
            # Write to system MOTD
            with open( self.system_motd, 'w' ) as f:
                f.write( new_content );
            
            return True;
            
        except (PermissionError, OSError) as e:
            return False;
    
    def _write_user_motd( self, signals_text: str ) -> bool:
        """Write to user MOTD file (~/.motd)"""
        
        try:
            # Write signals directly to user MOTD (no wrapping needed for user file)
            with open( self.user_motd, 'w' ) as f:
                f.write( signals_text.rstrip() + "\n" );
            
            # Make readable by user (no need for executable)
            self.user_motd.chmod( stat.S_IRUSR | stat.S_IWUSR );
            
            return True;
            
        except (PermissionError, OSError) as e:
            print( f"❌ Error writing user MOTD: {e}" );
            return False;
    
    def _write_btfd_motd( self, signals_text: str ) -> bool:
        """Write to BTFD-specific MOTD file"""
        
        try:
            wrapped_content = self._wrap_btfd_section( signals_text );
            
            with open( self.btfd_motd, 'w' ) as f:
                f.write( wrapped_content + "\n" );
            
            # Make readable by user
            self.btfd_motd.chmod( stat.S_IRUSR | stat.S_IWUSR );
            
            # Also create a simple display script
            display_script = self.btfd_motd.parent / "show_btfd_signals.sh";
            with open( display_script, 'w' ) as f:
                f.write( f"""#!/bin/bash
# BTFD Signal Display Script
echo "Reading BTFD signals from {self.btfd_motd}"
echo "=========================="
cat {self.btfd_motd}
echo ""
""" );
            
            display_script.chmod( stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR );
            
            return True;
            
        except (PermissionError, OSError) as e:
            return False;
    
    def _remove_btfd_section( self, content: str ) -> str:
        """Remove existing BTFD section from MOTD content"""
        
        lines = content.split( '\n' );
        cleaned_lines = [];
        in_btfd_section = False;
        
        for line in lines:
            if line.strip() == "# === BTFD Daily Signals ===":
                in_btfd_section = True;
                continue;
            elif line.strip() == "# === End BTFD Signals ===":
                in_btfd_section = False;
                continue;
            elif not in_btfd_section:
                cleaned_lines.append( line );
        
        return '\n'.join( cleaned_lines );
    
    def _wrap_btfd_section( self, signals_text: str ) -> str:
        """Wrap signals text in BTFD section markers"""
        
        return f"""# === BTFD Daily Signals ===
{signals_text.rstrip()}
# === End BTFD Signals ===""";
    
    def _ensure_bashrc_integration( self ) -> bool:
        """Ensure .bashrc integration is set up (internal method)"""
        
        try:
            bashrc_path = Path.home() / ".bashrc";
            
            # Read existing .bashrc
            bashrc_content = "";
            if bashrc_path.exists():
                with open( bashrc_path, 'r' ) as f:
                    bashrc_content = f.read();
            
            # Check if BTFD integration already exists
            if "# BTFD Daily Signals Integration" in bashrc_content:
                return True;  # Already set up
            
            # Add BTFD integration to display ~/.motd
            btfd_integration = f"""

# BTFD Daily Signals Integration
if [ -f "{self.user_motd}" ]; then
    cat "{self.user_motd}"
fi
""";
            
            # Append to .bashrc
            with open( bashrc_path, 'a' ) as f:
                f.write( btfd_integration );
            
            print( f"✅ BTFD integration added to .bashrc (displays {self.user_motd})" );
            return True;
            
        except (PermissionError, OSError) as e:
            print( f"⚠️  Warning: Could not set up .bashrc integration: {e}" );
            return False;
    
    def setup_bashrc_integration( self ) -> bool:
        """Setup .bashrc integration to show BTFD signals on login (public method)
        
        Returns:
            True if setup successfully, False otherwise
        """
        return self._ensure_bashrc_integration();
    
    def get_motd_status( self ) -> Dict[str, bool]:
        """Get status of different MOTD options"""
        
        status = {
            'system_motd_writable': os.access( str( self.system_motd.parent ), os.W_OK ),
            'user_motd_exists': self.user_motd.exists(),
            'btfd_motd_exists': self.btfd_motd.exists(),
            'bashrc_integrated': False
        };
        
        # Check if .bashrc has BTFD integration
        bashrc_path = Path.home() / ".bashrc";
        if bashrc_path.exists():
            try:
                with open( bashrc_path, 'r' ) as f:
                    status['bashrc_integrated'] = "BTFD Daily Signals Integration" in f.read();
            except:
                pass;
        
        return status;
    
    def show_setup_instructions( self ):
        """Show instructions for MOTD setup"""
        
        status = self.get_motd_status();
        
        print( "📋 BTFD MOTD Setup Status:" );
        print( "=" * 50 );
        
        if status['system_motd_writable']:
            print( "✅ System MOTD (/etc/motd) - Writable" );
        else:
            print( "❌ System MOTD (/etc/motd) - Not writable (need sudo)" );
        
        if status['user_motd_exists']:
            print( "✅ User MOTD (~/.motd) - Available" );
        else:
            print( "ℹ️  User MOTD (~/.motd) - Will be created" );
        
        if status['btfd_motd_exists']:
            print( "✅ BTFD MOTD (~/.btfd_motd) - Available" );
        else:
            print( "ℹ️  BTFD MOTD (~/.btfd_motd) - Will be created" );
        
        if status['bashrc_integrated']:
            print( "✅ .bashrc integration - Active" );
        else:
            print( "ℹ️  .bashrc integration - Available (run setup_bashrc_integration)" );
        
        print( "\n📖 Setup Instructions:" );
        print( "1. Primary: User MOTD (~/.motd) with bashrc integration (automatic)" );
        print( "2. Fallback: System MOTD (/etc/motd) requires sudo permissions" );
        print( "3. Manual setup: Run setup_bashrc_integration() if needed" );
        print( "4. View signals: cat ~/.motd or login to new shell session" );

# Convenience functions
def write_signals_to_motd( signals_text: str ) -> bool:
    """Write signals to user MOTD (~/.motd) with bashrc integration and system fallback"""
    
    writer = MOTDWriter();
    return writer.write_signals_to_motd( signals_text );

def setup_motd_integration() -> bool:
    """Setup complete MOTD integration"""
    
    writer = MOTDWriter();
    
    print( "🔧 Setting up BTFD MOTD integration..." );
    writer.show_setup_instructions();
    
    # Setup .bashrc integration
    return writer.setup_bashrc_integration();