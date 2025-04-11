import paramiko
from dataclasses import dataclass
from pathlib import Path


@dataclass 
class SSHConfig: 
    hostname: str
    username: str 
    password: str = None
    key_filename: Path | str = None
    port: int = 22

    def __post_init__(self): 
        if not (self.password or self.key_filename) or (self.password and self.key_filename): 
            raise ValueError("You must provide one of [password] OR [(private) key path]")


class SSH: 

    @staticmethod
    def connect(ssh_config: SSHConfig) -> paramiko.client.SSHClient: 
        connection_params = ssh_config.__dict__.copy()
        try: 
            conn = paramiko.SSHClient()
            conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Filter connection params
            if "password" in connection_params and not connection_params["password"]: 
                del connection_params["password"]
            if "key_filename" in connection_params and not connection_params["key_filename"]: 
                del connection_params["key_filename"]

            conn.connect(**connection_params)
            return conn
    
        except paramiko.AuthenticationException as auth_exception:
            raise Exception(f"Authentication failed: {auth_exception}")
        except paramiko.SSHException as ssh_exception:
            raise Exception(f"SSH exception: {ssh_exception}")
        except Exception as e:
            raise Exception(f"Error: {e}")