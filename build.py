"""
Google Ads Helper - Build Script
Automates frontend build + PyInstaller packaging
"""

import subprocess
import sys
import os
import shutil

def run_command(cmd, cwd=None, description=""):
    """Run shell command and handle errors"""
    if description:
        print(f"\n{'='*60}")
        print(f"  {description}")
        print('='*60)

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            shell=True,
            capture_output=False
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Command failed: {' '.join(cmd)}")
        print(f"   Error code: {e.returncode}")
        return False

def build():
    """Main build function"""
    print("\n" + "="*60)
    print("  Google Ads Helper - Build Script")
    print("="*60)

    # 1. Check if we're in the right directory
    if not os.path.exists("frontend") or not os.path.exists("backend"):
        print("\n❌ Error: Must run from project root directory")
        print("   Expected folders: frontend/, backend/")
        sys.exit(1)

    # 2. Build frontend
    print("\n📦 Step 1/3: Building React frontend...")

    frontend_dir = os.path.abspath("frontend")

    # Check if npm is available
    try:
        subprocess.run(["npm", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\n❌ Error: npm not found")
        print("   Please install Node.js: https://nodejs.org/")
        sys.exit(1)

    # Install dependencies
    if not run_command(
        ["npm", "install"],
        cwd=frontend_dir,
        description="Installing frontend dependencies..."
    ):
        sys.exit(1)

    # Build
    if not run_command(
        ["npm", "run", "build"],
        cwd=frontend_dir,
        description="Building frontend (npm run build)..."
    ):
        sys.exit(1)

    # Verify dist exists
    dist_path = os.path.join(frontend_dir, "dist")
    if not os.path.exists(dist_path):
        print(f"\n❌ Error: Frontend build failed - {dist_path} not found")
        sys.exit(1)

    print(f"✅ Frontend build complete: {dist_path}")

    # 3. Clean previous PyInstaller builds
    print("\n🧹 Step 2/3: Cleaning previous builds...")

    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            print(f"   Removing {folder}/")
            shutil.rmtree(folder)

    for file in ["main.spec", "Google Ads Helper.spec"]:
        if os.path.exists(file):
            print(f"   Removing {file}")
            os.remove(file)

    # 4. Package with PyInstaller
    print("\n🔧 Step 3/3: Packaging with PyInstaller...")

    # Check if PyInstaller is available
    try:
        subprocess.run(["pyinstaller", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\n❌ Error: PyInstaller not found")
        print("   Install: pip install pyinstaller")
        sys.exit(1)

    # PyInstaller command
    # CRITICAL: --add-data precision
    # - Include frontend/dist (static assets)
    # - Include backend/app (Python code)
    # - EXCLUDE: __pycache__, .pyc, .env, database/, logs/
    # - Database & logs will be created in exe directory on first run

    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",               # Single .exe
        "--windowed",              # No console window (GUI mode)
        "--name", "Google Ads Helper",
        "--add-data", "frontend/dist;frontend/dist",
        "--add-data", "backend/app;backend/app",
        "--exclude-module", "pytest",
        "--exclude-module", "scipy",
        "--exclude-module", "sklearn",
        "--exclude-module", "matplotlib",
        # Add icon if exists
        # "--icon", "icon.ico",
        "main.py"
    ]

    if not run_command(
        pyinstaller_cmd,
        description="Running PyInstaller (this may take 2-5 minutes)..."
    ):
        sys.exit(1)

    # 5. Verify exe exists
    exe_path = os.path.join("dist", "Google Ads Helper.exe")
    if not os.path.exists(exe_path):
        print(f"\n❌ Error: Executable not found at {exe_path}")
        sys.exit(1)

    exe_size_mb = os.path.getsize(exe_path) / (1024 * 1024)

    # Success!
    print("\n" + "="*60)
    print("  ✅ Build Complete!")
    print("="*60)
    print(f"   Executable: {exe_path}")
    print(f"   Size: {exe_size_mb:.1f} MB")
    print("="*60)
    print("\n📝 IMPORTANT NOTES:")
    print("   - The .exe is PORTABLE - no installation needed")
    print("   - On first run, it will create database/ and logs/ folders")
    print("   - These folders will be in the same directory as the .exe")
    print("   - To distribute: just send the .exe file")
    print("\n🚀 To test: double-click on 'Google Ads Helper.exe'")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        build()
    except KeyboardInterrupt:
        print("\n\n⚠️  Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
