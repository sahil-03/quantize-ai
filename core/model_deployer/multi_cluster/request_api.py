# api_service.py
import time
import threading
import requests
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from request_queue import RequestQueue
from load_balancer import LoadBalancer
from deployment_manager import DeploymentManager
from auto_scaler import AutoScaler

app = FastAPI()

# Initialize components
request_queue = RequestQueue(redis_host='localhost', redis_port=6379)

deployment_manager = DeploymentManager(
    model_path="/home/sahil/test_models/llama_1b",
    inference_script="/home/sahil/win25-Team21/core/inference_engine/experimental/llama_inference.py",
    image_tag="quantize_ai:latest"
)

load_balancer = LoadBalancer(deployment_manager)

autoscaler = AutoScaler(
    request_queue=request_queue,
    deployment_manager=deployment_manager,
    min_replicas=1,
    max_replicas=10,
    scale_up_threshold=5,  
    scale_down_threshold=2 
)
autoscaler.start_monitoring(check_interval=10)

def process_requests():
    """Background task to process requests from the queue"""
    while True:
        # Get a request from the queue
        request = request_queue.dequeue_request()
        if not request:
            time.sleep(1)  # No requests, wait a bit
            continue
            
        # Get an endpoint from the load balancer
        endpoint = load_balancer.get_endpoint_for_request()
        if not endpoint:
            # No endpoints available, put the request back in the queue
            request_queue.enqueue_request(request['data'])
            time.sleep(5)  # Wait before trying again
            continue
            
        try:
            # Send the request to the endpoint
            response = requests.post(
                f"http://{endpoint}/query",
                json=request['data'],
                timeout=30
            )
            
            # Process the response (in a real system, you'd send this back to the client)
            print(f"Request {request['id']} processed with response status: {response.status_code}")
            
        except Exception as e:
            print(f"Error processing request {request['id']}: {str(e)}")
            # Optionally, put the request back in the queue for retry
            request_queue.enqueue_request(request['data'])
            
        finally:
            # Release the endpoint in the load balancer
            # This is important for the least_connections strategy
            if endpoint:
                instance_id = next(
                    (e["instance_id"] for e in deployment_manager.get_active_endpoints() 
                     if e["endpoint"] == endpoint),
                    None
                )
                if instance_id:
                    load_balancer.release_endpoint(instance_id)

# Start the request processor in a background thread
processor_thread = threading.Thread(target=process_requests)
processor_thread.daemon = True
processor_thread.start()

class QueryRequest(BaseModel):
    prompt: str
    max_length: int = 128
    temperature: float = 0.3
    top_p: float = 0.95
    top_k: int = 50
    num_return_sequences: int = 1

@app.post("/query")
async def query(request: QueryRequest, background_tasks: BackgroundTasks):
    """Endpoint to handle model queries"""
    # Enqueue the request
    request_id = request_queue.enqueue_request(request.dict())
    
    # Return immediately with a request ID
    return {
        "status": "queued",
        "request_id": request_id,
        "message": "Your request has been queued and will be processed shortly."
    }

@app.get("/status/{request_id}")
async def get_status(request_id: str):
    """Endpoint to check the status of a request"""
    # In a real implementation, you'd store request status in Redis or another database
    # For now, we'll just return a placeholder
    return {
        "status": "processing",
        "request_id": request_id
    }

@app.get("/queue/stats")
async def get_queue_stats():
    """Endpoint to get queue statistics"""
    queue_length = request_queue.get_queue_length()
    active_endpoints = deployment_manager.get_active_endpoints()
    
    return {
        "queue_length": queue_length,
        "active_replicas": len(active_endpoints),
        "endpoints": active_endpoints
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)