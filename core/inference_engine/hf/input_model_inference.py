import logging
import os
from contextlib import asynccontextmanager
from typing import List, Optional
import argparse
import importlib

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig, AutoModel
from transformers.models.auto.configuration_auto import CONFIG_MAPPING


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InferenceRequest(BaseModel):
    """Request model for inference API."""
    prompt: str
    max_length: int = Field(default=128, gt=0)
    temperature: float = Field(default=0.7, gt=0.0, le=1.0)
    top_p: float = Field(default=0.95, gt=0.0, le=1.0)
    top_k: int = Field(default=50, gt=0)
    num_return_sequences: int = Field(default=1, gt=0)

class InferenceResponse(BaseModel):
    """Response model for inference API."""
    generated_text: List[str]
    tokens_generated: int
    latency: float
    tps: float

class ModelManager:
    """Manages the LLaMA model and tokenizer."""
    def __init__(self):
        self.model: Optional[AutoModelForCausalLM] = None
        self.tokenizer: Optional[AutoTokenizer] = None

    def load_model(self) -> None:
        """Load the model and tokenizer from the specified path."""
        #model_path = os.getenv("MODEL_DIR", "/app/model")
        model_path = os.getenv("MODEL_DIR")
        logger.info("Loading model from %s", model_path)


        
        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)

            # First attempt: Use AutoModelForCausalLM directly
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.float16,
                device_map="auto",
                low_cpu_mem_usage=True
            )
            logger.info("Model loaded successfully with AutoModelForCausalLM.")

        except ValueError as e:
            logger.warning("AutoModelForCausalLM failed: %s", e)

            if "Unrecognized configuration class" in str(e):
                try:
                    # Extract the config class name from the error message
                    config_class_name = str(e).split("<class '")[1].split("'>")[0]
                    logger.info("Attempting to dynamically register %s", config_class_name)

                    # Dynamically import the config module
                    module_path = ".".join(config_class_name.split('.')[:-1])
                    class_name = config_class_name.split('.')[-1]
                    config_module = importlib.import_module(module_path)
                    config_class = getattr(config_module, class_name)

                    # Instantiate config to read the actual model_type
                    config_instance = config_class.from_pretrained(model_path)
                    correct_model_type = config_instance.model_type

                    # Use CONFIG_MAPPING instead of pretrained_config_archive_map
                    if correct_model_type in CONFIG_MAPPING:
                        existing_config_class = CONFIG_MAPPING[correct_model_type]
                        if existing_config_class == config_class:
                            logger.info("Config already registered and matches existing config.")
                        else:
                            # Conflict: Register under a new alias
                            unique_model_type = f"{correct_model_type}_custom"
                            AutoConfig.register(unique_model_type, config_class)
                            correct_model_type = unique_model_type
                            logger.info("Registered config under unique model_type: %s", unique_model_type)
                    else:
                        # Safe to register directly
                        AutoConfig.register(correct_model_type, config_class)
                        logger.info("Registered custom config with model_type: %s", correct_model_type)

                    # Load model using AutoModel with the registered config
                    self.model = AutoModel.from_pretrained(
                        model_path,
                        config=config_instance,
                        torch_dtype=torch.float16,
                        device_map="auto",
                        low_cpu_mem_usage=True
                    )
                    logger.info("Model loaded using custom registered config.")

                except Exception as reg_e:
                    logger.error("Failed to register custom config: %s", reg_e)
                    raise

            else:
                # If not a config issue, raise the original error
                logger.error("Failed to load model: %s", e)
                raise
        
        # try:
        #     self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        #     self.model = AutoModelForCausalLM.from_pretrained(
        #         model_path,
        #         torch_dtype=torch.float16,
        #         device_map="auto",
        #         low_cpu_mem_usage=True
        #     )
        #     self.model.eval()
        #     logger.info("Model and tokenizer loaded successfully!")
        
        # except Exception as e:
        #     logger.error("Error loading model: %s", str(e))
        #     raise

    def is_ready(self) -> bool:
        """Check if model and tokenizer are loaded."""
        return self.model is not None and self.tokenizer is not None

model_manager = ModelManager()
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Load model on startup."""
    global model_manager
    if model_manager is None:
        logger.error("Model manager is not initialized before startup.")
        raise RuntimeError("Model manager not initialized.")
    model_manager.load_model()

@app.post("/query", response_model=InferenceResponse)
async def query(request: InferenceRequest):
    """Handle inference requests."""
    if not model_manager.is_ready():
        raise HTTPException(
            status_code=500,
            detail="Model and tokenizer are not loaded."
        )
    
    logger.info("Processing inference request")
    try:
        start_time = torch.cuda.Event(enable_timing=True)
        end_time = torch.cuda.Event(enable_timing=True)
        start_time.record()

        inputs = model_manager.tokenizer(
            request.prompt,
            return_tensors="pt",
            padding=True,
            truncation=True
        )
        inputs = {k: v.to(model_manager.model.device) for k, v in inputs.items()}

        # Generate response
        with torch.no_grad():
            outputs = model_manager.model.generate(
                **inputs,
                max_length=request.max_length,
                temperature=request.temperature,
                top_p=request.top_p,
                top_k=request.top_k,
                num_return_sequences=request.num_return_sequences,
                pad_token_id=model_manager.tokenizer.pad_token_id,
                eos_token_id=model_manager.tokenizer.eos_token_id,
            )

        generated_texts = [
            model_manager.tokenizer.decode(output, skip_special_tokens=True)
            for output in outputs
        ]

        end_time.record()
        torch.cuda.synchronize()
        duration = start_time.elapsed_time(end_time) / 1000
        tokens_generated = outputs.shape[1] - inputs['input_ids'].shape[1]

        return InferenceResponse(
            generated_text=generated_texts,
            tokens_generated=tokens_generated,
            latency=duration,
            tps=tokens_generated / duration if duration > 0 else 0
        )

    except Exception as e:
        logger.exception("Error during inference: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Example of parsing command-line arguments")
    parser.add_argument('--model', type=str, required=True, help='Path or Hugging Face model name')
    args = parser.parse_args()
    os.environ["MODEL_DIR"] = args.model
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "input_model_inference:app",
        host="0.0.0.0",
        port=port,
        workers=1,
    )
