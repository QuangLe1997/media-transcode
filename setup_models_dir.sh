#!/bin/bash

# Script to setup models directory for face detection
echo "🔧 Setting up models directory for face detection..."

# Create models_faces directory if it doesn't exist
if [ ! -d "./models_faces" ]; then
    echo "📁 Creating models_faces directory..."
    mkdir -p ./models_faces
else
    echo "📁 models_faces directory already exists"
fi

# Set proper permissions
echo "🔐 Setting permissions for models_faces directory..."
chmod 755 ./models_faces

# Check if directory is writable
if [ -w "./models_faces" ]; then
    echo "✅ models_faces directory is writable"
else
    echo "❌ models_faces directory is not writable"
    echo "🔧 Trying to fix permissions..."
    sudo chmod 755 ./models_faces
    sudo chown -R $USER:$USER ./models_faces
fi

echo "✅ Models directory setup complete!"
echo "📋 Directory info:"
ls -la ./models_faces || echo "Directory is empty (models will be auto-downloaded)"