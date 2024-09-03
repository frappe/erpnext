# Goldfish ERP System

This project is a modern ERP system using FastAPI for the backend and React with shadcn UI for the frontend.

## Backend Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set up the database:
   ```
   alembic upgrade head
   ```

3. Run the FastAPI server:
   ```
   uvicorn goldfish.main:app --reload
   ```

## Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd goldfish-ui
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Run the development server:
   ```
   npm run dev
   ```

## Running Tests

Backend tests: