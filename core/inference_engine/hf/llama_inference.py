import logging
import os
import time
import importlib
from typing import List, Optional

import asyncio
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from transformers import TextIteratorStreamer
from threading import Thread

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig, AutoModel
from transformers.models.auto.configuration_auto import CONFIG_MAPPING
from core.common.logger import Logger 

logger = Logger(__name__, log_level="INFO", console_output=True)

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
    def __init__(self):
        self.model: Optional[AutoModelForCausalLM] = None
        self.tokenizer: Optional[AutoTokenizer] = None

    def load_model(self) -> None:
        # model_path = os.getenv("MODEL_DIR", "/app/model")
        model_path = "/home/sahil/test_models/llama_1b/"
        logger.info("Loading model from %s", model_path)

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)

            if self.tokenizer.pad_token is None:
                logger.info("No pad token found. Setting pad token to eos token.")
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.float16,
                device_map="auto",
                low_cpu_mem_usage=True
            )
            self.model.eval()
            logger.info("Model loaded successfully with AutoModelForCausalLM.")

        except ValueError as e:
            logger.warning("AutoModelForCausalLM failed: %s", e)

            if "Unrecognized configuration class" in str(e):
                try:
                    config_class_name = str(e).split("<class '")[1].split("'>")[0]
                    logger.info("Attempting to dynamically register %s", config_class_name)

                    module_path = ".".join(config_class_name.split('.')[:-1])
                    class_name = config_class_name.split('.')[-1]
                    config_module = importlib.import_module(module_path)
                    config_class = getattr(config_module, class_name)

                    config_instance = config_class.from_pretrained(model_path)
                    correct_model_type = config_instance.model_type

                    if correct_model_type in CONFIG_MAPPING:
                        existing_config_class = CONFIG_MAPPING[correct_model_type]
                        if existing_config_class == config_class:
                            logger.info("Config already registered and matches existing config.")
                        else:
                            unique_model_type = f"{correct_model_type}_custom"
                            AutoConfig.register(unique_model_type, config_class)
                            correct_model_type = unique_model_type
                            logger.info("Registered config under unique model_type: %s", unique_model_type)
                    else:
                        AutoConfig.register(correct_model_type, config_class)
                        logger.info("Registered custom config with model_type: %s", correct_model_type)

                    self.model = AutoModel.from_pretrained(
                        model_path,
                        config=config_instance,
                        torch_dtype=torch.float16,
                        device_map="auto",
                        low_cpu_mem_usage=True
                    )
                    self.model.eval()
                    logger.info("Model loaded using custom registered config.")

                except Exception as reg_e:
                    logger.error("Failed to register custom config: %s", reg_e)
                    raise

            else:
                logger.error("Failed to load model: %s", e)
                raise

    def is_ready(self) -> bool:
        return self.model is not None and self.tokenizer is not None


model_manager = ModelManager()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    model_manager.load_model()


#### API ENDPOINTS ####

@app.get("/health")
async def health():
    if model_manager.is_ready():
        return {"status": "ok"}
    else:
        raise HTTPException(
            status_code=500,
            detail="Model and tokenizer are not loaded."
        )


@app.post("/query")
async def query(request: InferenceRequest):
    if not model_manager.is_ready():
        raise HTTPException(
            status_code=500,
            detail="Model and tokenizer are not loaded."
        )
    
    logger.info("Processing inference request")
    try:
        # Timing logic
        if torch.cuda.is_available():
            start_time = torch.cuda.Event(enable_timing=True)
            end_time = torch.cuda.Event(enable_timing=True)
            start_time.record()
        else:
            start = time.perf_counter()

        # NEW PROMPT: Include full conversation history and instruct the model to focus on the latest question.
        model_prompt = f"""You are an advanced AI assistant. Respond concisely 
        and accurately, focusing on answering only the most recent question. Do 
        not repeat previous answers.
        
        Conversation History:
        {request.prompt}

        Assistant: """

        inputs = model_manager.tokenizer(
            model_prompt,
            return_tensors="pt",
            padding=True,
            truncation=True
        )
        inputs = {k: v.to(model_manager.model.device) for k, v in inputs.items()}

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
            model_manager.tokenizer.decode(output, skip_special_tokens=True) \
            .split("Assistant: ", 1)[-1].strip().split("User:", 1)[0].strip()
            for output in outputs
        ]

        if torch.cuda.is_available():
            end_time.record()
            torch.cuda.synchronize()
            duration = start_time.elapsed_time(end_time) / 1000
        else:
            duration = time.perf_counter() - start

        tokens_generated = outputs.shape[1] - inputs['input_ids'].shape[1]

        return {
            "generated_text": generated_texts,
            "tokens_generated": tokens_generated,
            "latency": duration,
            "tps": tokens_generated / duration if duration > 0 else 0
        }

    except Exception as e:
        logger.error("Error during inference: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))



# class StreamingInferenceRequest(BaseModel):
#     """Request model for streaming inference API."""
#     prompt: str
#     max_length: int = Field(default=128, gt=0)
#     temperature: float = Field(default=0.7, gt=0.0, le=1.0)
#     top_p: float = Field(default=0.95, gt=0.0, le=1.0)
#     top_k: int = Field(default=50, gt=0)

@app.post("/stream")
async def stream(request: InferenceRequest):
    if not model_manager.is_ready():
        raise HTTPException(
            status_code=500,
            detail="Model and tokenizer are not loaded."
        )
    logger.info("Processing streaming inference request")
    
    # NEW PROMPT for streaming: include full conversation history and instruction.
    model_prompt = (
        "You are an advanced AI assistant. Respond concisely and accurately, \
        focusing on answering only the most recent question. Do not repeat \
        previous answers.\n\n"
        "Conversation History:\n{prompt}\n\n"
        "Assistant: "
    ).format(prompt=request.prompt)
    
    inputs = model_manager.tokenizer(
        model_prompt,
        return_tensors="pt",
        padding=True,
        truncation=True
    )
    inputs = {k: v.to(model_manager.model.device) for k, v in inputs.items()}
    
    streamer = TextIteratorStreamer(
        model_manager.tokenizer,
        skip_prompt=True,
        skip_special_tokens=True
    )
    
    generation_kwargs = dict(
        **inputs,
        streamer=streamer,
        max_length=request.max_length,
        temperature=request.temperature,
        top_p=request.top_p,
        top_k=request.top_k,
        pad_token_id=model_manager.tokenizer.pad_token_id,
        eos_token_id=model_manager.tokenizer.eos_token_id,
    )
    
    thread = Thread(target=model_manager.model.generate, kwargs=generation_kwargs)
    thread.start()
    
    async def stream_generator():
        started = False
        full_text = ""
        for text in streamer:
            full_text += text
            if "User:" in full_text and started:
                remaining = full_text.split("User:", 1)[0].rstrip()
                if remaining:
                    yield remaining
                break
            if not started:
                if "Assistant: " in full_text:
                    started = True
                    response_part = full_text.split("Assistant: ", 1)[1]
                    if response_part:
                        yield response_part
            else:
                yield text
                await asyncio.sleep(0.001)
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
    )

# Run fastapi server
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(
        "core.inference_engine.hf.llama_inference:app",
        host="0.0.0.0",
        port=port,
        workers=1,
    )