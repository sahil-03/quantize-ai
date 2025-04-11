"""
Basic streamlit app to test e2e POC. 
"""
import requests
import streamlit as st 
import subprocess
import time

from core.model_deployer.deployer.deployer import ModelDeployer
from core.common.ssh import SSHConfig



def create_ssh_tunnel(hostname, username, key_filename, remote_port=8001, local_port=8001):
    """Create an SSH tunnel to the remote server."""
    tunnel_cmd = f"ssh -N -L {local_port}:localhost:{remote_port} -i {key_filename} {username}@{hostname}"
    tunnel_process = subprocess.Popen(tunnel_cmd, shell=True)
    time.sleep(2)
    return tunnel_process, local_port


def run_model(model_path: str, endpoint: str, private_key: str):
    # Run the deployer script
    # try:
    #     config = SSHConfig(
    #         hostname=endpoint,
    #         username="sahil",
    #         key_filename=private_key
    #     )

    #     inference_script = f"/home/sahil/win25-Team21/core/inference_engine/experimental/llama_inference.py"
    #     deployer = ModelDeployer(model_path, inference_script, config)
    #     deployer.deploy_model()
    
    # except Exception as e:
    #     print(f"Error: {e}")
    data = {
        "model": model_path, 
        "endpoint": endpoint, 
        "private_key": private_key
    }
    api_url = "http://35.225.28.0:8001/deploy"
    
    print(f"Attempting to connect to: {api_url}")
    print(f"With data: {data}")
    
    # First try a simple GET request to check if server is up
    try:
        print("Testing server availability with GET request...")
        health_check = requests.get(f"http://35.225.28.0:8001/health", 
                                   timeout=5, 
                                   verify=False)
        print(f"Server health check response: {health_check.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Server health check failed: {e}")
    
    # Now try the actual POST request with increased timeout
    try:
        print("Sending POST request to deploy endpoint...")
        response = requests.post(
            api_url, 
            json=data, 
            verify=False, 
            timeout=30  # Increased timeout to 30 seconds
        )
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code == 200:
            try:
                print(f"JSON response: {response.json()}")
            except ValueError:
                print("Response was not valid JSON")
        
    except requests.exceptions.Timeout:
        print("Error: Request timed out after 30 seconds. The server might be taking too long to respond.")
    except requests.exceptions.ConnectionError:
        print("Error: Failed to connect to the server. The server might be down or unreachable.")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")



st.title("Quanitize AI")

st.sidebar.title("Add a new model")
with st.sidebar.form("create_bot_form"):
        model_path = st.text_input(label="Model path", value="/home/sahil/test_models/llama_1b")
        endpoint = st.text_input(label="IP Address of compute cluster.", value="34.136.98.200")
        private_key = st.text_input(label="Path to SSH private key", value="/home/sahil/.ssh/sahil2")
        
        if st.form_submit_button("⏩️ Run model"): 
            run_model(model_path, endpoint, private_key)

if st.sidebar.button("⏩️ Create SSH Tunnel"):
    try:
        tunnel_process, local_port = create_ssh_tunnel(endpoint, "sahil", private_key)
        st.session_state.tunnel_process = tunnel_process
        st.session_state.local_endpoint = f"localhost:{local_port}"
        st.sidebar.success(f"SSH tunnel created! Using {st.session_state.local_endpoint}")
    except Exception as e:
        st.sidebar.error(f"Failed to create SSH tunnel: {str(e)}")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is your question?"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    try:
        api_endpoint = st.session_state.get("local_endpoint", f"{endpoint}:8001")

        # health_check = requests.get(
        #     f"http://{api_endpoint}/health",
        # )
        # health_check.raise_for_status()
        # print("HEALTH: {}".format(health_check.json()["response"]))
        
        # If health check passes, make the actual request
        response = requests.post(
            f"http://{api_endpoint}/query",
            json={
                "prompt": prompt,
                "max_length": 128,
                "temperature": 0.3,
                "top_p": 0.95,
                "top_k": 50,
                "num_return_sequences": 1
            },
        )
        response.raise_for_status()
        result = response.json()
        answer = result["generated_text"][0]
        latency = result["latency"]
        tps = result["tps"]
        print(f"Latency: {latency}")
        print(f"Toks/sec: {tps}")

    except requests.exceptions.ConnectTimeout:
        answer = "Connection timed out. This could be due to:\n1. Firewall rules blocking port 8001\n2. Security group settings\n3. Network connectivity issues"
    except requests.exceptions.ConnectionError as e:
        answer = f"Connection error. Please verify:\n1. The VM is running\n2. The Docker container is running\n3. Port 8001 is open\nError: {str(e)}"
    except requests.RequestException as e:
        answer = f"An error occurred: {str(e)}"

    with st.chat_message("assistant"):
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})