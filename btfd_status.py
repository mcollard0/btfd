#!/usr/bin/env python3
"""
BTFD System Status Checker
Quick status overview of the BTFD daily scanner system
"""

import os
import sys
from datetime import date, datetime
from pathlib import Path

def check_btfd_status():
    """Check and display BTFD system status"""
    
    print("🚀 BTFD System Status Check")
    print("=" * 50)
    print(f"📅 Date: {date.today()}")
    print(f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    # Check directory structure
    btfd_dir = Path("/ARCHIVE/Programming/btfd")
    logs_dir = btfd_dir / "logs" 
    charts_dir = btfd_dir / "charts"
    
    print("📁 Directory Structure:")
    print(f"   BTFD: {'✅' if btfd_dir.exists() else '❌'} {btfd_dir}")
    print(f"   Logs: {'✅' if logs_dir.exists() else '❌'} {logs_dir}")
    print(f"   Charts: {'✅' if charts_dir.exists() else '❌'} {charts_dir}")
    print()
    
    # Check Python environment
    venv_python = btfd_dir / "venv" / "bin" / "python"
    script_path = btfd_dir / "src" / "daily_btfd_scanner.py"
    
    print("🐍 Python Environment:")
    print(f"   Virtual Env: {'✅' if venv_python.exists() else '❌'} {venv_python}")
    print(f"   Main Script: {'✅' if script_path.exists() else '❌'} {script_path}")
    print()
    
    # Check recent logs
    print("📝 Recent Logs:")
    if logs_dir.exists():
        log_files = list(logs_dir.glob("btfd_daily_*.log"))
        if log_files:
            # Sort by modification time, newest first
            log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for log_file in log_files[:3]:  # Show last 3 days
                file_size = log_file.stat().st_size
                mod_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                print(f"   📄 {log_file.name} ({file_size} bytes) - {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("   ⚠️  No log files found")
    else:
        print("   ❌ Logs directory not found")
    print()
    
    # Check system MOTD
    motd_path = Path("/etc/motd")
    print("📢 System MOTD:")
    if motd_path.exists():
        try:
            with open(motd_path, 'r') as f:
                content = f.read()
            
            if "BTFD Daily Signals" in content:
                print("   ✅ BTFD signals present in /etc/motd")
                # Extract just the BTFD section
                lines = content.split('\n')
                in_btfd = False
                for line in lines:
                    if "# === BTFD Daily Signals ===" in line:
                        in_btfd = True
                        continue
                    elif "# === End BTFD Signals ===" in line:
                        break
                    elif in_btfd and line.strip():
                        print(f"   {line}")
            else:
                print("   ⚠️  No BTFD signals found in /etc/motd")
        except PermissionError:
            print("   ❌ Cannot read /etc/motd (permission denied)")
    else:
        print("   ❌ /etc/motd not found")
    print()
    
    # Check cron job
    import subprocess
    print("⏰ Cron Job Status:")
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            cron_content = result.stdout
            if "BTFD Daily Scanner" in cron_content:
                print("   ✅ BTFD cron job is installed")
                # Extract the cron line
                for line in cron_content.split('\n'):
                    if "daily_btfd_scanner.py" in line:
                        print(f"   📅 Schedule: {line}")
            else:
                print("   ⚠️  BTFD cron job not found")
        else:
            print("   ❌ Cannot read crontab")
    except Exception as e:
        print(f"   ❌ Error checking cron: {e}")
    print()
    
    # Check recent charts
    print("📊 Recent Charts:")
    if charts_dir.exists():
        chart_files = list(charts_dir.glob("*_signal_*.png"))
        if chart_files:
            chart_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for chart_file in chart_files[:3]:  # Show last 3 charts
                file_size = chart_file.stat().st_size / 1024  # KB
                mod_time = datetime.fromtimestamp(chart_file.stat().st_mtime)
                print(f"   📈 {chart_file.name} ({file_size:.0f}KB) - {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("   ⚠️  No chart files found")
    else:
        print("   ❌ Charts directory not found")
    print()
    
    print("🎯 BTFD Status Check Complete")

if __name__ == "__main__":
    check_btfd_status()