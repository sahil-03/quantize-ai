import os
import json
import time
import tempfile
import subprocess
import shutil
import uuid
import platform
from pathlib import Path
from typing import Optional, Tuple
from core.common.ssh import SSHConfig, SSH
from core.model_deployer.profiler.profiler import Profiler
from core.model_deployer.deployer.scripts import ALL_REQUIREMENTS, DEPLOYMENT_SCRIPT
from core.model_deployer.deployer.hf_utils import extract_repo_id
from core.common.logger import Logger
from core.common.port_utils import find_available_port, check_remote_port_availability

# Import the HfApi to query model info from Hugging Face Hub.
from huggingface_hub import HfApi

logger = Logger(__name__, log_level="INFO", console_output=True)

class ModelDeployer:
    def __init__(
        self, 
        model_path: Path | str, 
        inference_script: Path | str, 
        ssh_config: SSHConfig, 
        image_tag: str = "quantize_ai:latest", 
        is_hf: bool = False, 
        hf_token: str | None = None,
    ):
        self.model_path = model_path
        self.inference_script = inference_script
        self.image_tag = image_tag
        self.ssh_config = ssh_config
        self.is_hf = is_hf
        self.hf_token = hf_token

        ### PURNE AWAY ALL DOCKER IMAGES ON THIS MACHINE (to free memory) 
        subprocess.check_call("docker system prune -a -f", shell=True)
        
        # # Use provided ports or find available ones
        # self.local_port = find_available_port()
        # if not self.local_port:
        #     raise RuntimeError("No available local ports found")
        
        self.local_port = 8080

            
        # self.remote_port = find_available_remote_port(self.ssh_config)
        # if not self.remote_port:
        #     raise RuntimeError("No available remote ports found")
        self.remote_port = 8080

        # Perform early check if the model is from Hugging Face.
        if self.is_hf:
            repo_id = extract_repo_id(str(self.model_path))
            logger.info(f"Verifying accessibility of Hugging Face model '{repo_id}'.")
            try:
                model_info = HfApi().model_info(repo_id, token=self.hf_token)
            except Exception as e:
                raise ValueError(f"Failed to retrieve model info for '{repo_id}': {e}")
            if model_info.private and not self.hf_token:
                raise ValueError(f"The model '{repo_id}' is private and no HF token was provided.")
            else:
                logger.info(f"Model '{repo_id}' is accessible.")

        # Connect via SSH after model verification.
        self.conn = SSH.connect(ssh_config)
        
        profile_path = Path.home() / "prof.json"
        with open(profile_path) as f:
            prof = json.load(f)
        self.use_gpus = int(prof.get("gpu_count", 0)) > 0
        
        kernel_name = prof.get("kernel_name", "linux").lower()
        machine = prof.get("machine", "amd64").lower()

        # resolve darwin -> linux
        if kernel_name == "darwin":
            kernel_name = "linux"

        self.platform = f"{kernel_name}/{machine}"

        base_tar_name = image_tag.split(":")[0]
        self.local_tar_path = f"{base_tar_name}.tar"
        self.remote_tar_path = f"{base_tar_name}_remote.tar"

    def _exec_command(self, command: list[str], is_local: bool = False) -> Optional[tuple[str, str]]:
        try:
            if is_local:
                subprocess.check_call(command)
            else:
                # Join list to a command string for remote execution.
                _, stdout, stderr = self.conn.exec_command(" ".join(command))
                out_str = stdout.read().decode() if stdout else ""
                err_str = stderr.read().decode() if stderr else ""
                return out_str, err_str
        except subprocess.SubprocessError as e:
            logger.error(f"Error executing command: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

    def _ensure_local_docker_installed(self):
        logger.info("Checking if Docker is installed on local host.")
        try:
            subprocess.check_call(["docker", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info("Docker is installed on local host.")
        except FileNotFoundError:
            logger.error("Docker not found on local host.")
            if platform.system() == "Darwin":
                logger.error("Docker not installed on macOS. Please install Docker Desktop from https://www.docker.com/products/docker-desktop")
                raise EnvironmentError("Docker not installed on macOS.")
            else:
                logger.info("Installing Docker on local host...")
                install_cmd = "curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh && rm get-docker.sh"
                subprocess.check_call(install_cmd, shell=True)
                logger.info("Docker installed successfully on local host.")

    def _ensure_remote_packages_installed(self):
        logger.info("Ensuring Docker and rsync are installed on remote host.")
        # Check for Docker
        stdout, _ = self._exec_command(["command", "-v", "docker"], is_local=False)
        if stdout and stdout.strip():
            logger.info("Docker is installed on remote host.")
        else:
            logger.info("Docker not found on remote host. Installing Docker...")
            install_cmd = "curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh && rm get-docker.sh"
            self._exec_command(install_cmd.split(), is_local=False)
            logger.info("Docker installation attempted on remote host.")

        # Check for rsync
        stdout, _ = self._exec_command(["command", "-v", "rsync"], is_local=False)
        if stdout and stdout.strip():
            logger.info("rsync is installed on remote host.")
        else:
            logger.info("rsync not found on remote host. Installing rsync...")
            install_cmd = "sudo apt-get update && sudo apt-get install -y rsync"
            self._exec_command(install_cmd.split(), is_local=False)
            logger.info("rsync installation attempted on remote host.")

    def _build_docker_image(self):
        build_context = tempfile.mkdtemp()
        try:
            if self.is_hf:
                # For HF models, simply write out the repo id.
                repo_id = extract_repo_id(str(self.model_path))
                (Path(build_context) / "model").mkdir(parents=True, exist_ok=True)
                with open(Path(build_context) / "model" / "hf_model_link.txt", "w") as f:
                    f.write(repo_id)
            else:
                if Path(self.model_path).is_dir():
                    model_dest = Path(build_context) / "model"
                    shutil.copytree(self.model_path, model_dest)
                else:
                    (Path(build_context) / "model").mkdir(parents=True, exist_ok=True)
                    shutil.copy(self.model_path, Path(build_context) / "model" / Path(self.model_path).name)

            inference_script_dest = Path(build_context) / "llama_inference.py"
            shutil.copy(self.inference_script, inference_script_dest)

            requirements_path_dest = Path(build_context) / "requirements.txt"
            with open(requirements_path_dest, "w") as f:
                f.write(ALL_REQUIREMENTS)

            entrypoint_src = Path(__file__).parent / "entrypoint.sh"
            entrypoint_dest = Path(build_context) / "entrypoint.sh"
            shutil.copy(entrypoint_src, entrypoint_dest)

            # Copy the core directory (adjust the path as needed)
            core_src = Path(__file__).parent.parent.parent.resolve()
            core_dest = Path(build_context) / "core"
            shutil.copytree(core_src, core_dest)

            dockerfile_path = Path(build_context) / "Dockerfile"
            with open(dockerfile_path, "w") as f:
                f.write(DEPLOYMENT_SCRIPT)

            logger.info("Building docker image.")
            build_cmd = ["docker", "build", "--platform", self.platform, "-t", self.image_tag, build_context]
            self._exec_command(build_cmd, is_local=True)
            logger.info("Docker image built successfully!")
        finally:
            shutil.rmtree(build_context)

    def _save_docker_image(self):
        logger.info("Saving docker image to tarball.")
        save_cmd = ["docker", "save", "-o", self.local_tar_path, self.image_tag]
        self._exec_command(save_cmd, is_local=True)
        logger.info(f"Docker image saved to {self.local_tar_path}")

    def _transfer_docker_image(self):
        cmd = [
            "rsync",
            "-avzP",
            "--timeout=120",
            "--partial",
            "--progress",
            "-e", f"ssh -i {self.ssh_config.key_filename}",
            self.local_tar_path,
            f"{self.ssh_config.username}@{self.ssh_config.hostname}:{self.remote_tar_path}"
        ]
        logger.info("Transferring tarball via rsync.")
        self._exec_command(cmd, is_local=True)
        logger.info(f"Tarball transferred to remote host at {self.remote_tar_path}")

    def _load_docker_image(self):
        logger.info("Loading docker image on remote host.")
        load_cmd = ["sudo", "docker", "load", "-i", self.remote_tar_path]
        stdout, load_err = self._exec_command(load_cmd, is_local=False)
        if load_err and load_err.strip():
            logger.error(f"Error loading docker image on remote host: {load_err}")
        else:
            logger.info("Docker image loaded on remote host.")

    def _run_docker_image(self) -> str:
        logger.info("Running docker container on remote host.")
        run_cmd = ["sudo", "docker", "run"]
        if self.use_gpus:
            run_cmd.extend(["--gpus", "all"])
        # Pass HF_TOKEN into the container; the entrypoint will handle the model download.
        if self.hf_token:
            run_cmd.extend(["-e", f"HF_TOKEN={self.hf_token}"])
        # Pass the port as an environment variable to the container
        run_cmd.extend(["-e", f"PORT={self.remote_port}"])
        run_cmd.extend(["-d", "-p", f"{self.remote_port}:{self.remote_port}", self.image_tag])
        container_id, run_err = self._exec_command(run_cmd, is_local=False)
        if run_err and run_err.strip():
            logger.error(f"Error running docker container on remote host: {run_err}")
            container_id = ""
        else:
            container_id = container_id.strip()
            logger.info(f"Docker container started with ID: {container_id}")
        return container_id

    def create_ssh_tunnel(self):
        """Create SSH tunnel using the configured local and remote ports."""
        tunnel_cmd = [
            "ssh",
            "-N",
            "-L", f"{self.local_port}:localhost:{self.remote_port}",
            "-i", self.ssh_config.key_filename,
            f"{self.ssh_config.username}@{self.ssh_config.hostname}"
        ]
        logger.info(f"Creating SSH tunnel from local port {self.local_port} to remote port {self.remote_port}.")
        tunnel_process = subprocess.Popen(tunnel_cmd)
        time.sleep(2)
        logger.info(f"SSH tunnel established on localhost:{self.local_port} forwarding to remote port {self.remote_port}")
        # Print a special message that can be parsed by the server to extract the port
        print(f"TUNNEL_PORT:{self.local_port}")
        return tunnel_process, self.local_port

    def deploy_model(self, tunnel: bool = False, prune: bool = False):
        try:
            self._ensure_local_docker_installed()
            for fn in ["_build", "_save"]:
                getattr(self, f"{fn}_docker_image")()
            self._ensure_remote_packages_installed()
            for fn in ["_transfer", "_load", "_run"]:
                container_id = getattr(self, f"{fn}_docker_image")() or ""
            if tunnel:
                tunnel_process, local_port = self.create_ssh_tunnel()
                try:
                    logger.info("Waiting for docker container to exit.")
                    wait_cmd = ["sudo", "docker", "wait", container_id]
                    stdout, _ = self._exec_command(wait_cmd, is_local=False)
                    exit_code = stdout.strip() if stdout else "unknown"
                    logger.info(f"Container {container_id} exited with code {exit_code}")
                finally:
                    tunnel_process.terminate()
                    logger.info("SSH tunnel closed.")
            if prune:
                for _ in range(10):
                    check_cmd = ["sudo", "docker", "ps", "-a", "-q", "--filter", f"id={container_id}"]
                    stdout, _ = self._exec_command(check_cmd, is_local=False)
                    if not stdout.strip():
                        break
                    logger.info("Waiting for container to be removed...")
                    time.sleep(2)
                else:
                    logger.info(f"Forcing removal of container {container_id}.")
                    self._exec_command(["sudo", "docker", "rm", "-f", container_id], is_local=False)
                remove_cmd = ["sudo", "docker", "rmi", "-f", self.image_tag]
                stdout, remove_err = self._exec_command(remove_cmd, is_local=False)
                if remove_err and remove_err.strip():
                    logger.error(f"Error pruning docker image: {remove_err}")
                else:
                    logger.info("Docker image pruned successfully.")
        finally:
            self._exec_command(["rm", self.remote_tar_path], is_local=False)
            self.conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Deploy model to remote server")
    parser.add_argument("--user", type=str, required=False, help="Username for local paths")
    parser.add_argument("--host", type=str, required=True, help="Remote host IP address")
    parser.add_argument("--ssh-user", type=str, required=True, help="SSH username for remote host")
    parser.add_argument("--ssh-key", type=str, required=True, help="Path to SSH key file")
    parser.add_argument("--model-dir", type=str, required=True, help="Path to model directory or HF model URL")
    parser.add_argument("--hf", action="store_true", help="Indicate model-dir is a Hugging Face URL")
    parser.add_argument("--hf-token", type=str, default=None, help="Hugging Face access token (if needed)")
    parser.add_argument("--tunnel", action="store_true", help="Create SSH tunnel on local port after deployment")
    parser.add_argument("--prune", action="store_true", help="Prune docker image after container exits")
    args = parser.parse_args()

    model_path = args.model_dir
    base_dir = Path(__file__).parent.parent.parent
    inference_script = (base_dir / "inference_engine" / "hf" / "llama_inference.py").resolve()
    # inference_script = (base_dir / "inference_engine" / "vllm" / "vllm_inference.py").resolve()

    ssh_config = SSHConfig(
        hostname=args.host,
        username=args.ssh_user,
        key_filename=args.ssh_key,
        port=22
    )

    profiler = Profiler(ssh_config)
    profiler.profile()

    md = ModelDeployer(model_path, inference_script, ssh_config, is_hf=args.hf, hf_token=args.hf_token)
    md.deploy_model(tunnel=args.tunnel, prune=args.prune)