import logging
import requests
from typing import Dict, Any  # Add type hints

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Constants in UPPERCASE
IP_ADDRESS = "34.136.98.200"
PORT = 8000

def get_default_payload() -> Dict[str, Any]:
    """Return default inference request payload."""
    return {
        "prompt": "Hey! How's it going?",
        "max_length": 128,
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 50,
        "num_return_sequences": 1
    }

def main() -> None:
    """Send test inference request to local LLaMA endpoint."""
    url = f"http://{IP_ADDRESS}:{PORT}/query"
    payload = get_default_payload()
    
    try:
        logger.info("Sending request to: %s", url)
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print("Inference result:\n{}".format(result["response"]))
        else:
            logger.error("Error: Received status code %d", response.status_code)
            logger.error("Response: %s", response.text)
    
    except Exception as e:
        logger.exception("An error occurred during the request: %s", str(e))

def test_batch_inference():
    """Test batch inference endpoint."""
    url = f"http://{IP_ADDRESS}:{PORT}/batch_query"
    payload = {
        "prompts": [
            "What is machine learning?",
            "Explain neural networks",
            "Define deep learning",
            "What is AI?"
        ],
        "max_length": 128,
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 50,
        "num_return_sequences": 1,
        "batch_size": 2  # Process 2 prompts at a time
    }
    
    try:
        logger.info("Sending batch request to: %s", url)
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            for i, texts in enumerate(result["generated_texts"]):
                logger.info("Results for prompt %d:", i + 1)
                for text in texts:
                    logger.info("%s", text)
            logger.info("Average latency: %.3f seconds", result["average_latency"])
            logger.info("Average tokens per second: %.2f", result["average_tps"])
        else:
            logger.error("Error: Received status code %d", response.status_code)
            logger.error("Response: %s", response.text)
    
    except Exception as e:
        logger.exception("An error occurred during the batch request: %s", str(e))

if __name__ == '__main__':
    main()