import requests
import json
import time
import argparse

def test_health(base_url):
    response = requests.get(f"{base_url}/health")
    print(f"Health check status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_inference(base_url, prompt="What is 5+5?", max_tokens=50):
    payload = {
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    
    print(f"Sending inference request with prompt: {prompt}")
    start_time = time.time()
    response = requests.post(f"{base_url}/query", json=payload)
    duration = time.time() - start_time
    
    print(f"Inference status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Completion: {result['response']['completion']}")
        print(f"Tokens generated: {result['response']['tokens_generated']}")
        print(f"Latency: {result['response']['latency']:.2f}s")
        print(f"Tokens per second: {result['response']['tps']:.2f}")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test vLLM Inference API")
    parser.add_argument("--url", type=str, default="http://localhost:8000",
                       help="Base URL of the inference API (default: http://localhost:8000)")
    parser.add_argument("--prompt", type=str, default="Hello, I am a language model",
                       help="Prompt for inference (default: 'Hello, I am a language model')")
    parser.add_argument("--max-tokens", type=int, default=50,
                       help="Maximum number of tokens to generate (default: 50)")
    
    args = parser.parse_args()
    
    if test_health(args.url):
        print("\nHealth check passed. Testing inference...")
        test_inference(args.url, args.prompt, args.max_tokens)
    else:
        print("\nHealth check failed. Please check if the server is running.")
