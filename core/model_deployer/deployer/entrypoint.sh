#!/bin/bash
set -e

# If a Hugging Face model link is provided, clone the repository
if [ -f /app/model/hf_model_link.txt ]; then
  echo "Detected Hugging Face model link. Cloning model repository..."
  MODEL_REPO=$(cat /app/model/hf_model_link.txt)
  if [ -n "$HF_TOKEN" ]; then
    echo "Using provided HF_TOKEN for authentication."
    huggingface-cli login --token "$HF_TOKEN"
    huggingface-cli download "$MODEL_REPO" --token "$HF_TOKEN" --local-dir /app/model
  else
    huggingface-cli download "$MODEL_REPO" --local-dir /app/model
  fi
fi

# Use PORT environment variable if set, otherwise default to 8000
PORT=${PORT:-8080}
echo "Starting uvicorn server on port $PORT..."
exec uvicorn llama_inference:app --host 0.0.0.0 --port $PORT