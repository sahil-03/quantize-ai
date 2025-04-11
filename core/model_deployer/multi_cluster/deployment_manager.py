# deployment_manager.py
import time
import json
from typing import List, Dict
from core.model_deployer.deployer.deployer import ModelDeployer
from core.common.ssh import SSHConfig

class DeploymentManager:
    def __init__(self, 
                 model_path: str,
                 inference_script: str,
                 image_tag: str = "quantize_ai:latest",
                 is_hf: bool = False,
                 hf_token: str = None):
        self.model_path = model_path
        self.inference_script = inference_script
        self.image_tag = image_tag
        self.is_hf = is_hf
        self.hf_token = hf_token
        self.deployments = {}  # Maps instance_id -> deployment info
        
        # Load cluster configuration
        self.clusters = self._load_cluster_config()
        
    def _load_cluster_config(self):
        """Load cluster configuration from a config file"""
        # In a real implementation, this would load from a config file
        # For now, we'll use a hardcoded example
        return [
            {
                "id": "cluster1",
                "hostname": "34.136.98.200",
                "username": "sahil",
                "key_filename": "/home/sahil/.ssh/sahil2"
            },
            # Add more clusters as needed
        ]
        
    def scale_deployment(self, target_replicas: int):
        """Scale the deployment to the target number of replicas"""
        current_replicas = len(self.deployments)
        
        if target_replicas > current_replicas:
            # Scale up
            self._add_replicas(target_replicas - current_replicas)
        elif target_replicas < current_replicas:
            # Scale down
            self._remove_replicas(current_replicas - target_replicas)
            
    def _add_replicas(self, count: int):
        """Add new replicas to the deployment"""
        for _ in range(count):
            # Select a cluster to deploy to (simple round-robin for now)
            cluster_index = len(self.deployments) % len(self.clusters)
            cluster = self.clusters[cluster_index]
            
            # Create SSH config
            ssh_config = SSHConfig(
                hostname=cluster["hostname"],
                username=cluster["username"],
                key_filename=cluster["key_filename"]
            )
            
            # Deploy the model
            try:
                deployer = ModelDeployer(
                    model_path=self.model_path,
                    inference_script=self.inference_script,
                    ssh_config=ssh_config,
                    image_tag=self.image_tag,
                    is_hf=self.is_hf,
                    hf_token=self.hf_token
                )
                
                # Deploy and get container ID
                container_id = deployer.deploy_model()
                
                # Store deployment info
                instance_id = f"{cluster['id']}-{container_id[:12]}"
                self.deployments[instance_id] = {
                    "container_id": container_id,
                    "cluster": cluster,
                    "ssh_config": ssh_config,
                    "endpoint": f"{cluster['hostname']}:8000",
                    "status": "running",
                    "created_at": time.time()
                }
                
                print(f"Added new replica: {instance_id}")
                
            except Exception as e:
                print(f"Failed to add replica: {str(e)}")
                
    def _remove_replicas(self, count: int):
        """Remove replicas from the deployment"""
        # Get the oldest replicas to remove
        replicas_to_remove = sorted(
            self.deployments.items(),
            key=lambda x: x[1]["created_at"]
        )[:count]
        
        for instance_id, deployment in replicas_to_remove:
            try:
                # Create SSH connection
                ssh_config = deployment["ssh_config"]
                container_id = deployment["container_id"]
                
                # Stop and remove the container
                from core.common.ssh import SSH
                conn = SSH.connect(ssh_config)
                
                # Stop the container
                _, stdout, stderr = conn.exec_command(f"sudo docker stop {container_id}")
                if stderr and stderr.read():
                    print(f"Warning stopping container {container_id}: {stderr.read().decode()}")
                    
                # Remove the container
                _, stdout, stderr = conn.exec_command(f"sudo docker rm {container_id}")
                if stderr and stderr.read():
                    print(f"Warning removing container {container_id}: {stderr.read().decode()}")
                
                # Remove from deployments
                del self.deployments[instance_id]
                print(f"Removed replica: {instance_id}")
                
            except Exception as e:
                print(f"Failed to remove replica {instance_id}: {str(e)}")
                
    def get_active_endpoints(self) -> List[Dict]:
        """Get a list of all active endpoints"""
        return [
            {
                "instance_id": instance_id,
                "endpoint": info["endpoint"],
                "cluster": info["cluster"]["id"]
            }
            for instance_id, info in self.deployments.items()
            if info["status"] == "running"
        ]