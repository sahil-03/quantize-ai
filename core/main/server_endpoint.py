import os
import shutil
import uvicorn
import logging
import subprocess
import tempfile
import sys
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from pydantic import BaseModel
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# parser = argparse.ArgumentParser(description="Deploy model to remote server")
#     parser.add_argument("--user", type=str, required=True, help="Username for local paths")
#     parser.add_argument("--host", type=str, required=True, help="Remote host IP address")
#     parser.add_argument("--ssh-user", type=str, required=True, help="SSH username for remote host")
#     parser.add_argument("--ssh-key", type=str, required=True, help="Path to SSH key file")
#     parser.add_argument("--model-dir", type=str, required=True, help="Path to model directory or HF model URL")
#     parser.add_argument("--hf", action="store_true", help="Indicate model-dir is a Hugging Face URL")
#     parser.add_argument("--hf-token", type=str, default=None, help="Hugging Face access token (if needed)")
#     parser.add_argument("--tunnel", action="store_true", help="Create SSH tunnel on port 8000 after deployment")
#     parser.add_argument("--prune", action="store_true", help="Prune docker image after container exits")
#     args = parser.parse_args()

class DeploymentConfig(BaseModel): 
    host: str
    ssh_user: str
    ssh_key: str
    model_source: str  # 'huggingface' or 'local'
    hf: Optional[str] = None
    hf_token: Optional[str] = None
    model_file_path: Optional[str] = None

class SSHKeyTransfer(BaseModel):
    source_path: str
    target_host: str
    target_user: str = "root"

@app.post("/upload-ssh-key")
async def upload_ssh_key(sshKey: UploadFile = File(...)):
    """
    Endpoint to handle SSH key file uploads.
    Saves the uploaded key to a temporary location and returns the path.
    """
    try:
        # Create a temp directory to store the key
        temp_dir = tempfile.mkdtemp(prefix="ssh_keys_")
        key_path = os.path.join(temp_dir, "id_rsa")
        
        # Save the uploaded file
        with open(key_path, "wb") as f:
            content = await sshKey.read()
            f.write(content)
        
        # Set proper permissions for SSH key
        os.chmod(key_path, 0o600)
        
        logger.info(f"Saved uploaded SSH key to {key_path}")
        
        return {
            "status": "success",
            "message": "SSH key uploaded successfully",
            "key_path": key_path
        }
    except Exception as e:
        logger.error(f"Error uploading SSH key: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to upload SSH key: {str(e)}"
        }

@app.post("/upload-model-file")
async def upload_model_file(model_file: UploadFile = File(...)):
    try:
        # Create uploads directory if it doesn't exist
        os.makedirs("/tmp/model_uploads", exist_ok=True)
        
        # Generate a unique filename
        file_extension = os.path.splitext(model_file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = f"/tmp/model_uploads/{unique_filename}"
        
        # Write the file to disk
        with open(file_path, "wb") as f:
            content = await model_file.read()
            f.write(content)
        
        # Set appropriate permissions
        os.chmod(file_path, 0o600)
        
        # Return the path to the uploaded file
        return {"status": "success", "file_path": file_path}
    except Exception as e:
        logger.error(f"Error uploading model file: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post("/deploy")
async def deploy_model(deployment_config: DeploymentConfig):
    deployment_script = os.path.expanduser("~/win25-Team21/core/model_deployer/deployer/deployer.py")
    command = [
        "python", 
        deployment_script, 
        f"--host {deployment_config.host}",
        f"--ssh-user {deployment_config.ssh_user}",
        f"--ssh-key {deployment_config.ssh_key}",
        f"--model-dir {deployment_config.hf}",
        "--hf"
    ]
    
    # Only add hf_token if it's provided
    if deployment_config.hf_token and deployment_config.hf_token.strip():
        command.append(f"--hf-token {deployment_config.hf_token}")
    
    # Add additional flags
    command.extend(["--tunnel", "--prune"])
    
    # logger.info(f"Running deployment command: {' '.join(command)}")
    
    # try: 
    #     result = subprocess.check_output(" ".join(command), shell=True, stderr=subprocess.STDOUT, text=True)
    #     logger.info(f"Deployment result: {result}")
    #     return {"Response": "Successfully deployed model!", "details": result}
    # except subprocess.CalledProcessError as e:
    #     error_message = f"Command returned error (code {e.returncode}): {e.output}"
    #     logger.error(error_message)
    #     return {"Response": "Failed to deploy model", "error": error_message}

    logger.info(f"Running deployment command: {' '.join(command)}")
    
    try: 
        # Use subprocess.Popen to capture output in real-time
        process = subprocess.Popen(
            " ".join(command), 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            bufsize=1, 
            universal_newlines=True
        )
        
        # Capture all output
        output_lines = []
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            output_line = line.strip()
            output_lines.append(output_line)
            # Print to console in real-time
            logger.info(output_line)
        
        # Wait for process to complete
        return_code = process.wait()
        
        # Check if command was successful
        if return_code == 0:
            result = "\n".join(output_lines)
            logger.info("Deployment successful")
            return {"Response": "Successfully deployed model!", "details": result}
        else:
            error_message = f"Command returned error (code {return_code})"
            logger.error(error_message)
            return {"Response": "Failed to deploy model", "error": error_message, "details": "\n".join(output_lines)}
            
    except subprocess.CalledProcessError as e:
        error_message = f"Command returned error (code {e.returncode}): {e.output}"
        logger.error(error_message)
        return {"Response": "Failed to deploy model", "error": error_message}
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        logger.error(error_message)
        return {"Response": "Failed to deploy model", "error": error_message}



@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("server_endpoint:app", host="0.0.0.0", port=8000)