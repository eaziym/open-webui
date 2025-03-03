# Setting Up Open WebUI Locally

This guide will help you set up and run Open WebUI on your local machine.

## Prerequisites

- Git
- Node.js and npm
- Python 3.8+ with pip
- Virtual environment tool (venv)

## Step 1: Clone the Repository

```bash
git clone https://github.com/eaziym/open-webui
cd open-webui
```

## Step 2: Set Up the Frontend

```bash
# Install frontend dependencies
npm install

# Start the development server
npm run dev
```

This will start the frontend development server at http://localhost:5173.

## Step 3: Set Up the Backend

```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Start the backend development server
sh dev.sh
```

This will start the backend server at http://localhost:8080.

## Step 4: Access the Application

With both the frontend and backend servers running, you can access the application at http://localhost:5173.

## Troubleshooting

- If you encounter any port conflicts, make sure no other applications are using ports 5173 or 8080.
- If you're having issues with dependencies, try clearing npm and pip caches and reinstalling.
- For more detailed troubleshooting, check the error logs in your terminal windows.

## Development Workflow

1. Make changes to the code
2. The development servers will automatically reload to reflect your changes
3. For backend changes that require restarting the server, press Ctrl+C in the backend terminal and run `sh dev.sh` again
