# BlueTrivia Frontend

This is the admin interface and statistics dashboard for BlueTrivia.

## Setup Instructions

1. Make sure you have Python 3.10+ installed

2. Install dependencies:

   ```bash
   # Option 1: Using the install script
   chmod +x install_frontend_deps.sh
   ./install_frontend_deps.sh

   # Option 2: Manual installation
   pip install -r frontend/requirements.txt
   ```

3. Run the frontend server:

   ```bash
   python run_frontend.py
   ```

4. Access the interfaces:
   - Admin interface: http://localhost:8000/admin
     - Default credentials: admin/changeme
   - Public stats: http://localhost:8000/public

## Directory Structure
