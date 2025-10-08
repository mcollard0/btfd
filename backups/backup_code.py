#!/usr/bin/env python3
"""
BTFD Backup System - Automated code snapshots
Creates timestamped backups of source code before major changes
Implements retention policy: 50 copies for <150KB files, 25 for larger files
"""

import os
import zipfile
import datetime
import glob
import sys
from pathlib import Path

def get_file_size( filepath ):
    """Get file size in KB"""
    return os.path.getsize( filepath ) / 1024

def should_backup( filepath ):
    """Check if file should be backed up based on modification time"""
    # Get last modification time
    mod_time = datetime.datetime.fromtimestamp( os.path.getmtime( filepath ) )
    now = datetime.datetime.now()
    
    # Backup if modified in last hour or if forced
    return ( now - mod_time ).total_seconds() < 3600

def create_backup( source_dir, backup_dir ):
    """Create timestamped backup of source directory"""
    
    # Create backup directory if it doesn't exist
    os.makedirs( backup_dir, exist_ok=True );
    
    # Generate timestamp
    timestamp = datetime.datetime.now().strftime( "%Y-%m-%dT%H%M%S" );
    backup_name = f"src.{timestamp}.zip";
    backup_path = os.path.join( backup_dir, backup_name );
    
    # Create zip file
    with zipfile.ZipFile( backup_path, 'w', zipfile.ZIP_DEFLATED ) as zipf:
        for root, dirs, files in os.walk( source_dir ):
            # Skip __pycache__ and .git directories
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'venv']];
            
            for file in files:
                if file.endswith( ( '.py', '.md', '.txt', '.json', '.yaml', '.yml' ) ):
                    file_path = os.path.join( root, file );
                    arc_path = os.path.relpath( file_path, source_dir );
                    zipf.write( file_path, arc_path );
    
    backup_size_kb = get_file_size( backup_path );
    print( f"✅ Created backup: {backup_name} ({backup_size_kb:.1f} KB)" );
    
    return backup_path, backup_size_kb;

def cleanup_old_backups( backup_dir ):
    """Remove old backups based on retention policy"""
    
    # Get all backup files sorted by creation time (newest first)
    backup_files = glob.glob( os.path.join( backup_dir, "src.*.zip" ) );
    backup_files.sort( key=os.path.getctime, reverse=True );
    
    files_removed = 0;
    
    for i, backup_file in enumerate( backup_files ):
        file_size_kb = get_file_size( backup_file );
        
        # Determine retention limit based on file size
        if file_size_kb < 150:
            retention_limit = 50;
        else:
            retention_limit = 25;
        
        # Remove files beyond retention limit
        if i >= retention_limit:
            try:
                os.remove( backup_file );
                print( f"🗑️  Removed old backup: {os.path.basename( backup_file )}" );
                files_removed += 1;
            except OSError as e:
                print( f"❌ Error removing {backup_file}: {e}" );
    
    if files_removed > 0:
        print( f"📦 Cleaned up {files_removed} old backup(s)" );

def main():
    """Main backup function"""
    
    # Get current directory (should be BTFD project root)
    current_dir = os.getcwd();
    project_root = Path( current_dir );
    
    # Verify we're in the right directory
    if not ( project_root / "src" ).exists():
        print( "❌ Error: Must be run from BTFD project root directory" );
        sys.exit( 1 );
    
    source_dir = project_root / "src";
    backup_dir = project_root / "backups";
    
    print( f"🔄 Starting backup process..." );
    print( f"📂 Source: {source_dir}" );
    print( f"📂 Backup: {backup_dir}" );
    
    # Create backup
    backup_path, backup_size_kb = create_backup( str( source_dir ), str( backup_dir ) );
    
    # Cleanup old backups
    cleanup_old_backups( str( backup_dir ) );
    
    # Show current backup count
    backup_count = len( glob.glob( str( backup_dir / "src.*.zip" ) ) );
    print( f"📊 Total backups: {backup_count}" );
    print( f"✅ Backup complete!" );

if __name__ == "__main__":
    main();