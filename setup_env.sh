#!/bin/bash

# Create conda environment
echo "Creating conda environment 'mcp-moat' with Python 3.11..."
conda create -n mcp-moat python=3.11 -y

# Activate the environment
echo "Activating conda environment..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate mcp-moat

# Install requirements
echo "Installing requirements from requirements.txt..."
pip install -r requirements.txt

# Install whisper (not in requirements.txt but needed)
echo "Installing openai-whisper..."
pip install openai-whisper

echo "Environment setup complete. Activate it with: conda activate mcp-moat"
