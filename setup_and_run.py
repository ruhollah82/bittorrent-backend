#!/usr/bin/env python3
"""
Cross-platform setup and run script for BitTorrent Backend
Supports Windows, Linux, and macOS
"""

import os
import sys
import subprocess
import platform
import shutil
import time
from pathlib import Path


class SetupRunner:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / 'venv'
        self.env_file = self.project_root / '.env'
        self.requirements_file = self.project_root / 'requirements.txt'

        # Platform detection
        self.system = platform.system().lower()
        self.is_windows = self.system == 'windows'
        self.is_linux = self.system == 'linux'
        self.is_macos = self.system == 'darwin'

        print(f"🐧 Detected platform: {self.system}")
        print(f"📁 Project root: {self.project_root}")

    def run_command(self, command, cwd=None, shell=False, check=True, env=None):
        """Run a command with cross-platform compatibility"""
        try:
            if self.is_windows and not shell:
                # Use shell=True on Windows for better compatibility
                shell = True

            print(f"🔧 Running: {' '.join(command) if isinstance(command, list) else command}")
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                shell=shell,
                check=check,
                capture_output=True,
                text=True,
                env=env
            )
            return result
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {e}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
            raise

    def check_python_version(self):
        """Check if Python version is compatible"""
        version = sys.version_info
        if version < (3, 8):
            print(f"❌ Python {version.major}.{version.minor} is not supported. Please use Python 3.8 or higher.")
            sys.exit(1)
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")

    def setup_virtual_environment(self):
        """Create and setup virtual environment"""
        if self.venv_path.exists():
            print("✅ Virtual environment already exists")
            return

        print("🏗️  Creating virtual environment...")

        if self.is_windows:
            python_cmd = "python"
        else:
            python_cmd = "python3"

        self.run_command([python_cmd, "-m", "venv", str(self.venv_path)])
        print("✅ Virtual environment created")

    def install_dependencies(self):
        """Install Python dependencies"""
        print("📦 Installing dependencies...")

        if self.is_windows:
            pip_path = self.venv_path / "Scripts" / "pip"
            python_path = self.venv_path / "Scripts" / "python"
        else:
            pip_path = self.venv_path / "bin" / "pip"
            python_path = self.venv_path / "bin" / "python"

        # Upgrade pip first
        self.run_command([str(python_path), "-m", "pip", "install", "--upgrade", "pip"])

        # Install requirements
        if self.requirements_file.exists():
            try:
                self.run_command([str(python_path), "-m", "pip", "install", "-r", str(self.requirements_file)])
            except subprocess.CalledProcessError:
                print("⚠️  Some dependencies might already be installed or have version conflicts")
                print("🔄 Continuing with setup...")
        else:
            print("⚠️  requirements.txt not found, installing basic Django packages...")
            self.run_command([str(python_path), "-m", "pip", "install", "django", "djangorestframework"])

        print("✅ Dependencies installed")

    def setup_environment_file(self):
        """Create .env file from example if it doesn't exist"""
        if self.env_file.exists():
            print("✅ Environment file already exists")
            return

        env_example = self.project_root / 'env.example'
        if env_example.exists():
            print("📋 Creating .env file from env.example...")
            shutil.copy(env_example, self.env_file)
            print("✅ Environment file created")
        else:
            print("⚠️  env.example not found, creating basic .env file...")
            basic_env = """# Django Settings
SECRET_KEY=django-insecure-dev-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,testserver

# Database (SQLite for development)
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# Redis (optional for development)
REDIS_URL=redis://127.0.0.1:6379/1
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
"""
            self.env_file.write_text(basic_env)
            print("✅ Basic environment file created")

    def run_migrations(self):
        """Run Django migrations"""
        print("🗄️  Running database migrations...")

        if self.is_windows:
            python_path = self.venv_path / "Scripts" / "python"
        else:
            python_path = self.venv_path / "bin" / "python"

        manage_py = self.project_root / "manage.py"

        # Run migrations
        self.run_command([str(python_path), str(manage_py), "migrate"])
        print("✅ Database migrations completed")

    def create_superuser(self):
        """Create Django superuser"""
        print("👤 Creating superuser...")

        if self.is_windows:
            python_path = self.venv_path / "Scripts" / "python"
        else:
            python_path = self.venv_path / "bin" / "python"

        manage_py = self.project_root / "manage.py"

        # Check if superuser already exists
        try:
            result = self.run_command([
                str(python_path), str(manage_py), "shell", "-c",
                "from django.contrib.auth import get_user_model; User = get_user_model(); print('Superuser exists' if User.objects.filter(is_superuser=True).exists() else 'No superuser')"
            ], check=False)

            if "Superuser exists" in result.stdout:
                print("✅ Superuser already exists")
                return
        except:
            pass  # Continue with creation

        # Create superuser
        env = os.environ.copy()
        env['DJANGO_SUPERUSER_USERNAME'] = 'admin'
        env['DJANGO_SUPERUSER_EMAIL'] = 'admin@example.com'
        env['DJANGO_SUPERUSER_PASSWORD'] = 'admin123'

        try:
            self.run_command([
                str(python_path), str(manage_py), "createsuperuser",
                "--username", "admin",
                "--email", "admin@example.com",
                "--noinput"
            ], env=env)
            print("✅ Superuser created (username: admin, password: admin123)")
        except subprocess.CalledProcessError:
            print("⚠️  Superuser creation failed or already exists")

    def setup_admin_panel(self):
        """Setup admin panel configurations"""
        print("⚙️  Setting up admin panel...")

        if self.is_windows:
            python_path = self.venv_path / "Scripts" / "python"
        else:
            python_path = self.venv_path / "bin" / "python"

        manage_py = self.project_root / "manage.py"

        try:
            self.run_command([str(python_path), str(manage_py), "setup_admin"])
            print("✅ Admin panel configured")
        except subprocess.CalledProcessError:
            print("⚠️  Admin panel setup failed")

    def create_invite_codes(self):
        """Create some invite codes for testing"""
        print("🎫 Creating invite codes...")

        if self.is_windows:
            python_path = self.venv_path / "Scripts" / "python"
        else:
            python_path = self.venv_path / "bin" / "python"

        manage_py = self.project_root / "manage.py"

        try:
            self.run_command([
                str(python_path), str(manage_py), "create_invite",
                "--count", "5",
                "--expires", "30",
                "--created-by", "admin"
            ])
            print("✅ Invite codes created")
        except subprocess.CalledProcessError:
            print("⚠️  Invite code creation failed")

    def show_invite_code(self):
        """Show the first available invite code"""
        if self.is_windows:
            python_path = self.venv_path / "Scripts" / "python"
        else:
            python_path = self.venv_path / "bin" / "python"

        manage_py = self.project_root / "manage.py"

        print("🎫 Getting first invite code...")
        try:
            self.run_command([
                str(python_path), str(manage_py), "show_invite_codes",
                "--first-only"
            ])
        except subprocess.CalledProcessError:
            print("⚠️  Could not retrieve invite code")

    def start_server(self):
        """Start the Django development server"""
        print("🚀 Starting Django development server...")

        if self.is_windows:
            python_path = self.venv_path / "Scripts" / "python"
        else:
            python_path = self.venv_path / "bin" / "python"

        manage_py = self.project_root / "manage.py"

        print("🌐 Server will be available at: http://127.0.0.1:8000")
        print("📖 API Documentation: http://127.0.0.1:8000/api/docs/")
        print("👤 Admin panel: http://127.0.0.1:8000/admin/")
        print("🔑 Superuser: admin / admin123")

        # Show invite code for first user registration
        self.show_invite_code()
        print("")

        try:
            # Start server
            self.run_command([
                str(python_path), str(manage_py), "runserver",
                "127.0.0.1:8000"
            ], check=False)  # Don't check since server runs indefinitely
        except KeyboardInterrupt:
            print("\n👋 Server stopped")

    def run_setup(self):
        """Run the complete setup process"""
        print("🎯 BitTorrent Backend Setup & Run Script")
        print("=" * 50)

        try:
            self.check_python_version()
            self.setup_virtual_environment()
            self.install_dependencies()
            self.setup_environment_file()
            self.run_migrations()
            self.create_superuser()
            self.setup_admin_panel()
            self.create_invite_codes()

            print("\n🎉 Setup completed successfully!")
            print("\nStarting server...\n")

            self.start_server()

        except Exception as e:
            print(f"\n❌ Setup failed: {e}")
            print("Please check the error messages above and try again.")
            sys.exit(1)


def main():
    runner = SetupRunner()
    runner.run_setup()


if __name__ == "__main__":
    main()
