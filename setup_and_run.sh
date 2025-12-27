#!/bin/bash

# BitTorrent Backend Setup and Run Script (Unix-like systems)
# Compatible with Linux and macOS

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 BitTorrent Backend Setup & Run Script${NC}"
echo "=================================================="

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    print_error "Unsupported OS: $OSTYPE"
    exit 1
fi

print_info "Detected OS: $OS"

# Check Python version
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "Python is not installed. Please install Python 3.8 or higher."
        exit 1
    fi

    # Check version
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oP '\d+\.\d+')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ $PYTHON_MAJOR -lt 3 ] || ([ $PYTHON_MAJOR -eq 3 ] && [ $PYTHON_MINOR -lt 8 ]); then
        print_error "Python $PYTHON_VERSION is not supported. Please use Python 3.8 or higher."
        exit 1
    fi

    print_status "Python $PYTHON_VERSION detected"
}

# Setup virtual environment
setup_venv() {
    if [ -d "venv" ]; then
        print_status "Virtual environment already exists"
        return
    fi

    print_info "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    print_status "Virtual environment created"
}

# Activate virtual environment
activate_venv() {
    print_info "Activating virtual environment..."
    source venv/bin/activate
    print_status "Virtual environment activated"
}

# Install dependencies
install_deps() {
    print_info "Installing dependencies..."

    # Upgrade pip
    pip install --upgrade pip

    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        print_warning "requirements.txt not found, installing basic packages..."
        pip install django djangorestframework
    fi

    print_status "Dependencies installed"
}

# Setup environment file
setup_env() {
    if [ -f ".env" ]; then
        print_status "Environment file already exists"
        return
    fi

    if [ -f "env.example" ]; then
        print_info "Creating .env file from env.example..."
        cp env.example .env
    else
        print_warning "env.example not found, creating basic .env file..."
        cat > .env << EOF
# Django Settings
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
EOF
    fi

    print_status "Environment file created"
}

# Run migrations
run_migrations() {
    print_info "Running database migrations..."
    python manage.py migrate
    print_status "Database migrations completed"
}

# Create superuser
create_superuser() {
    print_info "Checking for superuser..."

    # Check if superuser exists
    if python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); exit(0 if User.objects.filter(is_superuser=True).exists() else 1)" 2>/dev/null; then
        print_status "Superuser already exists"
        return
    fi

    print_info "Creating superuser..."
    echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | python manage.py shell
    print_status "Superuser created (username: admin, password: admin123)"
}

# Setup admin panel
setup_admin() {
    print_info "Setting up admin panel..."
    python manage.py setup_admin 2>/dev/null || print_warning "Admin panel setup failed"
    print_status "Admin panel configured"
}

# Create invite codes
create_invites() {
    print_info "Creating invite codes..."
    python manage.py create_invite --count 5 --expires 30 --created-by admin 2>/dev/null || print_warning "Invite code creation failed"
    print_status "Invite codes created"
}

# Start server
start_server() {
    echo ""
    print_status "Setup completed successfully!"
    echo ""
    print_info "Starting Django development server..."
    echo ""
    print_info "🌐 Server will be available at: http://127.0.0.1:8000"
    print_info "📖 API Documentation: http://127.0.0.1:8000/api/docs/"
    print_info "👤 Admin panel: http://127.0.0.1:8000/admin/"
    print_info "🔑 Superuser: admin / admin123"
    echo ""

    python manage.py runserver 127.0.0.1:8000
}

# Main execution
main() {
    check_python
    setup_venv
    activate_venv
    install_deps
    setup_env
    run_migrations
    create_superuser
    setup_admin
    create_invites
    start_server
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n👋 Script interrupted by user"; exit 1' INT

# Run main function
main
