#!/bin/bash
set -e

echo "Building ERIK ERP frontend..."
cd frontend
npm install
npm run build
cd ..
echo "Frontend build complete!"
