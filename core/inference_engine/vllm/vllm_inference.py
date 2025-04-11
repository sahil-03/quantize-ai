import logging
import os
import time
import importlib
import argparse
import torch
import uvicorn
from vllm import LLM, SamplingParams 
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from vllm_model_manager import VLLMModelManager, VLLMModelConfig
from contextlib import asynccontextmanager
from typing import List, Optional
from dataclasses import dataclass


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


############################
#    vLLM MODEL MANAGER    #
############################

@dataclass 
class VLLMModelConfig: 
    model_id: str 
    weights_path: str 
    tensor_parallel_size: int = 1 
    gpu_mem_utilization: float = 0.9 
    max_model_len: int = 2048 
    quantization: str = None 
    dtype: str = "auto"
    trust_remote_code: bool = True
    device: str = None  


class VLLMModelManager: 
    def __init__(self, config = VLLMModelConfig): 
        self.config = config
        self.model = None

        if self.config.device is None:
            self.config.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_cpu = self.config.device == "cpu"

    def load_model(self): 
        logger.info(f"Loading model: {self.config.model_id}")
        logger.info(f"Using device: {self.config.device}")

        try: 
            self._load_with_vllm()   
            logger.info("Model loaded successfully.")
        except Exception as e: 
            logger.error(f"Error loading model: {e}")
            raise
    
    def _load_with_vllm(self):
        logger.info("Loading model with vLLM")
        
        if self.is_cpu:
            logger.info(f"Using weights_path for CPU inference: {self.config.weights_path}")
            
            model_kwargs = {
                "model": self.config.weights_path,
                "dtype": "float32", 
                "device": self.config.device,
                "max_model_len": self.config.max_model_len,
                "disable_async_output_proc": True, 
            }
            
            logger.info(f"CPU model configuration: {model_kwargs}")
            self.model = LLM(**model_kwargs)
        else:
            logger.info(f"Using weights_path for GPU inference: {self.config.weights_path}")

            model_kwargs = {
                "model": self.config.weights_path,
                "tensor_parallel_size": self.config.tensor_parallel_size,
                "gpu_memory_utilization": self.config.gpu_mem_utilization,
                "trust_remote_code": self.config.trust_remote_code,
                "device": self.config.device,
            }
            
            # TODO: find a better way to integrate additional parameters
            if self.config.max_model_len is not None:
                model_kwargs["max_model_len"] = self.config.max_model_len
            if self.config.quantization is not None:
                model_kwargs["quantization"] = self.config.quantization
            if self.config.dtype != "auto":
                model_kwargs["dtype"] = self.config.dtype
            
            logger.info(f"GPU model configuration: {model_kwargs}")
        
        # Create model
        self.model = LLM(**model_kwargs)

    def is_ready(self): 
        return self.model is not None 
    
    async def generate(self, request: dict) -> dict: 
        prompt = request.get("prompt", "")
        
        try: 
            start = time.time()

            sampling_params = SamplingParams(
                temperature=request.get("temperature", 1.0),
                top_p=request.get("top_p", 1.0),
                max_tokens=request.get("max_tokens", 16),
                stop=request.get("stop", None),
                presence_penalty=request.get("presence_penalty", 0.0),
                frequency_penalty=request.get("frequency_penalty", 0.0),
                top_k=request.get("top_k", -1)
            )
            
            if self.is_cpu:
                logger.info("Using synchronous generation for CPU")
                outputs = self.model.generate(prompt, sampling_params)
            else:
                logger.info("Using asynchronous generation for GPU")
                outputs = await self.model.generate_async(prompt, sampling_params)
                
            duration = time.time() - start
            generated_text = outputs[0].outputs[0].text 
            tokens_generated = len(generated_text)
            tps = tokens_generated / duration if duration > 0 else 0
            
            return {
                "completion": generated_text,
                "tokens_generated": tokens_generated,
                "latency": duration,
                "tps": tps
            }

        except Exception as e: 
            logger.error(f"Error generating response: {e}")
            raise
    

############################
#    FAST API APP SETUP    #
############################

def parse_args():
    parser = argparse.ArgumentParser(description="vLLM Inference Server")
    parser.add_argument("--model-id", type=str, default=os.environ.get("MODEL_ID", "meta-llama/Llama-3.2-1B"),
                    help="Model ID (default: meta-llama/Llama-3.2-1B)")
    parser.add_argument("--weights-path", type=str, default=os.environ.get("WEIGHTS_PATH", "/home/sahil/test_models/llama_1b"),
                    help="Path to model weights (default: ./models/llama_1b)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)),
                    help="Port to run the server on (default: 8000)")
    parser.add_argument("--device", type=str, default=os.environ.get("DEVICE", None),
                    help="Device to use for inference (default: auto-detect)")
    parser.add_argument("--max-model-len", type=int, default=int(os.environ.get("MAX_MODEL_LEN", 2048)),
                    help="Maximum model length to use (default: 2048)")
    return parser.parse_args()


# Define model manager
args = parse_args()
model_manager = VLLMModelManager(
    VLLMModelConfig(
        model_id=args.model_id,
        weights_path=args.weights_path,
        device=args.device,
        max_model_len=args.max_model_len,
    )
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        model_manager.load_model()
        logger.info("Model loaded successfully during startup")
        yield
    except Exception as e:
        logger.error(f"Failed to load model during startup: {e}")
        raise
    finally:
        logger.info("Shutting down the application")

app = FastAPI(lifespan=lifespan)


#################
# API ENDPOINTS #
#################

class GenerationRequest(BaseModel):
    prompt: str
    temperature: float = 0.01
    top_p: float = 1.0
    max_tokens: int = 16
    stop: Optional[List[str]] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    top_k: int = -1


@app.get("/health")
async def health():
    if model_manager.is_ready():
        return {
            "status": "ok", 
            "device": model_manager.config.device,
            "model_id": model_manager.config.model_id,
            "weights_path": model_manager.config.weights_path
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Model is not loaded."
        )


@app.post("/query")
async def query(request: GenerationRequest):
    if not model_manager.is_ready():
        raise HTTPException(
            status_code=500,
            detail="Model is not loaded."
        )
    
    logger.info(f"Processing inference request with prompt: {request.prompt[:50]}...")
    try:
        response = await model_manager.generate(request.dict())
        return {"response": response}
    except Exception as e:
        logger.error(f"Error during inference: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Run fastapi server
if __name__ == "__main__":
    logger.info(f"Starting vLLM inference server on port {args.port}")
    logger.info(f"Model ID: {args.model_id}")
    logger.info(f"Weights path: {args.weights_path}")
    logger.info(f"Device: {args.device if args.device else 'auto-detect'}")
    logger.info(f"Max model length: {args.max_model_len}")
    
    uvicorn.run(
        "vllm_inference:app",
        host="0.0.0.0",
        port=args.port,
        workers=1,
    )
