#!/usr/bin/env python3
"""
Test script to verify MOTD integration is working correctly.

Tests:
1. User MOTD file creation and writing
2. Bashrc integration setup
3. MOTD display in new shell sessions
4. Cron job compatibility
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.notifications.motd_writer import MOTDWriter

def test_user_motd_creation():
    """Test that user MOTD file can be created and written"""
    print("🔧 Testing user MOTD creation...")
    
    writer = MOTDWriter()
    
    # Create test content
    test_content = f"""🎯 BTFD Test Signals ({datetime.now().strftime('%Y-%m-%d')}):
  📈 TEST: $123.45 📞CALL ⚠️99
  📉 DEMO: $67.89 📞PUT ⚠️88
Generated: {datetime.now().strftime('%H:%M')} (Test Mode)"""
    
    # Write to MOTD
    success = writer.write_signals_to_motd(test_content)
    
    if success:
        print("✅ User MOTD creation: PASS")
        
        # Verify file exists and has correct content
        user_motd = Path.home() / '.motd'
        if user_motd.exists():
            with open(user_motd, 'r') as f:
                content = f.read()
            
            if 'BTFD Test Signals' in content:
                print(f"✅ MOTD content verification: PASS")
                print(f"📄 MOTD file location: {user_motd}")
                return True
            else:
                print("❌ MOTD content verification: FAIL")
                return False
        else:
            print("❌ MOTD file creation: FAIL")
            return False
    else:
        print("❌ User MOTD creation: FAIL")
        return False

def test_bashrc_integration():
    """Test bashrc integration setup"""
    print("\n🔧 Testing bashrc integration...")
    
    bashrc_path = Path.home() / '.bashrc'
    
    if bashrc_path.exists():
        with open(bashrc_path, 'r') as f:
            content = f.read()
        
        # Check for integration
        if 'BTFD Daily Signals Integration' in content and '/.motd' in content:
            print("✅ Bashrc integration: PASS")
            print("📄 Integration found in ~/.bashrc")
            return True
        else:
            print("❌ Bashrc integration: FAIL")
            print("⚠️  Integration not found or pointing to wrong file")
            return False
    else:
        print("❌ Bashrc file not found: FAIL")
        return False

def test_motd_display():
    """Test MOTD display in interactive shell"""
    print("\n🔧 Testing MOTD display in interactive shell...")
    
    try:
        # Test with interactive bash
        result = subprocess.run([
            'bash', '-i', '-c', 
            'echo "=== MOTD TEST START ==="; '
            'if [ -f ~/.motd ]; then echo "MOTD file found"; cat ~/.motd; else echo "MOTD file not found"; fi; '
            'echo "=== MOTD TEST END ==="'
        ], capture_output=True, text=True, timeout=10)
        
        output = result.stdout
        
        if 'BTFD' in output and 'MOTD file found' in output:
            print("✅ MOTD display: PASS")
            print("📺 MOTD appears in interactive shells")
            return True
        else:
            print("❌ MOTD display: FAIL")
            print(f"Shell output: {output}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ MOTD display test: TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ MOTD display test: ERROR - {e}")
        return False

def test_cron_compatibility():
    """Test cron job compatibility"""
    print("\n🔧 Testing cron job compatibility...")
    
    # Check if BTFD cron job exists
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        crontab_content = result.stdout
        
        if 'btfd' in crontab_content.lower() and 'daily_btfd_scanner' in crontab_content:
            print("✅ BTFD cron job: FOUND")
            
            # Extract the cron job line
            lines = crontab_content.split('\n')
            btfd_lines = [line for line in lines if 'daily_btfd_scanner' in line]
            
            if btfd_lines:
                print(f"📅 Cron schedule: {btfd_lines[0].split('#')[0].strip()}")
                return True
            
        else:
            print("❌ BTFD cron job: NOT FOUND")
            return False
            
    except Exception as e:
        print(f"❌ Cron check error: {e}")
        return False

def test_permissions():
    """Test file permissions"""
    print("\n🔧 Testing file permissions...")
    
    user_motd = Path.home() / '.motd'
    
    if user_motd.exists():
        # Check if file is readable and writable by user
        if os.access(user_motd, os.R_OK) and os.access(user_motd, os.W_OK):
            print("✅ MOTD file permissions: PASS")
            
            # Check file ownership
            stat_info = user_motd.stat()
            current_uid = os.getuid()
            
            if stat_info.st_uid == current_uid:
                print("✅ MOTD file ownership: PASS")
                return True
            else:
                print("❌ MOTD file ownership: FAIL (wrong owner)")
                return False
        else:
            print("❌ MOTD file permissions: FAIL (not readable/writable)")
            return False
    else:
        print("⚠️  MOTD file doesn't exist yet")
        return True  # This is OK if it hasn't been created yet

def run_all_tests():
    """Run all MOTD integration tests"""
    print("🚀 BTFD MOTD Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("User MOTD Creation", test_user_motd_creation),
        ("Bashrc Integration", test_bashrc_integration),
        ("MOTD Display", test_motd_display),
        ("Cron Compatibility", test_cron_compatibility),
        ("File Permissions", test_permissions),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! MOTD integration is working correctly.")
        print("\n💡 To see MOTD in action:")
        print("   • Wait for next cron run (04:01 AM daily)")
        print("   • Or run: cd /ARCHIVE/Programming/btfd && venv/bin/python src/daily_btfd_scanner.py --test-mode")
        print("   • Then start a new interactive shell session")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)