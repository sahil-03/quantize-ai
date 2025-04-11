# DEPLOYMENT_SCRIPT = """
# FROM python:3.10-slim

# WORKDIR /app
# ENV PYTHONPATH=/app

# # Install curl to enable model download commands in the container.
# RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# # Copy the requirements file first to leverage Docker cache.
# COPY requirements.txt /app/requirements.txt

# # Install Python dependencies.
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy the model directory, inference script, and entrypoint script into the container.
# COPY model /app/model
# COPY core /app/core
# COPY llama_inference.py /app/llama_inference.py
# COPY entrypoint.sh /app/entrypoint.sh
# RUN chmod +x /app/entrypoint.sh

# # Set environment variable to let the inference script know where the model is.
# ENV MODEL_DIR=/app/model

# # Expose the API port.
# EXPOSE 8000

# # Run the entrypoint script.
# CMD ["/app/entrypoint.sh"]
# """

# ALL_REQUIREMENTS = """
# torch
# transformers
# fastapi
# uvicorn
# pydantic
# sentencepiece
# accelerate
# protobuf
# safetensors
# huggingface_hub
# vllm
# """


DEPLOYMENT_SCRIPT = """
FROM python:3.10-slim

WORKDIR /app
ENV PYTHONPATH=/app

# Install curl to enable model download commands in the container.
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to leverage Docker cache.
COPY requirements.txt /app/requirements.txt

# Install Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the model directory, inference script, and entrypoint script into the container.
COPY model /app/model
COPY core /app/core
COPY llama_inference.py /app/llama_inference.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set environment variable to let the inference script know where the model is.
ENV MODEL_DIR=/app/model

# Default port (can be overridden at runtime)
ENV PORT=8000

# Expose ports dynamically (actual binding happens at runtime)
# We'll use a wide range to accommodate different port selections
EXPOSE 8000-9000 50051

# Run the entrypoint script.
CMD ["/app/entrypoint.sh"]
"""

ALL_REQUIREMENTS = """
torch
transformers
fastapi
uvicorn
pydantic
sentencepiece
accelerate
protobuf
safetensors
huggingface_hub
"""