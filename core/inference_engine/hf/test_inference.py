import argparse
import requests
import time
import sys
from core.common.logger import Logger

logger = Logger(__name__, log_level="INFO", console_output=True)

IP_ADDRESS = "localhost"
PORT = 8000

def get_default_payload(prompt: str) -> dict:
    """
    Get the default payload for the inference request.
    
    Args:
        prompt: The prompt to send for inference.
        
    Returns:
        dict: The payload for the inference request.
    """
    return {
        "prompt": prompt,
        "max_length": 2048,
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 50,
        # "num_return_sequences": 1
    }

def main() -> None:
    parser = argparse.ArgumentParser(description='Test the inference API.')
    parser.add_argument('--prompt', type=str, required=True, help='The prompt to send for inference.')
    args = parser.parse_args()

    url = f"http://{IP_ADDRESS}:{PORT}/stream"
    payload = get_default_payload(args.prompt)
    
    try:
        logger.info("Sending request to %s", url)
        start_time = time.time()
        
        # Use requests.get with stream=True
        response = requests.post(url, json=payload, stream=True)
        
        if response.status_code == 200:
            logger.info("Streaming response started:")
            print("\n--- Response ---")
            
            # Use the raw response to read byte by byte
            for line in response.raw.read_chunked(1024):
                try:
                    # Decode the bytes to string
                    text = line.decode('utf-8')
                    # Print each chunk immediately
                    sys.stdout.write(text)
                    sys.stdout.flush()
                except UnicodeDecodeError:
                    # Handle potential decoding errors
                    pass
            
            print("\n--- End of response ---\n")
            
            # Print timing information
            elapsed_time = time.time() - start_time
            print(f"Total time: {elapsed_time:.2f} seconds")
        else:
            logger.error("Error: Received status code %d", response.status_code)
            logger.error("Response: %s", response.text)
    
    except Exception as e:
        logger.exception("An error occurred during the request: %s", str(e))

if __name__ == "__main__":
    main()