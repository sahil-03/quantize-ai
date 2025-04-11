import socket
import logging
from typing import Optional, Tuple

def find_available_port(start_port: int = 8000, end_port: int = 9000) -> Optional[int]:
    """
    Find an available local port within the specified range.
    
    Args:
        start_port: The lower bound of the port range to search.
        end_port: The upper bound of the port range to search.
        
    Returns:
        An available local port number or None if no ports are available.
    """
    for port in range(start_port, end_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.1)
            result = sock.connect_ex(('127.0.0.1', port))
            if result != 0:  # Port is available locally
                return port
    return None

def check_remote_port_availability(ssh_conn, port: int) -> bool:
    """
    Check if a port is available on a remote machine via SSH.
    
    Args:
        ssh_conn: SSH connection object.
        port: Port to check.
        
    Returns:
        True if the port is available, False otherwise.
    """
    try:
        # Use netstat to check if the port is in use on the remote host
        cmd = f"netstat -tuln | grep ':{port} '"
        _, stdout, _ = ssh_conn.exec_command(cmd)
        output = stdout.read().decode()
        # If output is empty, the port is available
        return not output.strip()
    except Exception as e:
        logging.error(f"Error checking remote port availability: {e}")
        # If there's an error, assume the port is not available to be safe
        return False

def find_available_remote_port(ssh_conn, start_port: int = 8000, end_port: int = 9000) -> Optional[int]:
    """
    Find an available remote port within the specified range by checking via SSH.
    
    Args:
        ssh_conn: SSH connection object.
        start_port: The lower bound of the port range to search.
        end_port: The upper bound of the port range to search.
        
    Returns:
        An available remote port number or None if no ports are available.
    """
    for port in range(start_port, end_port + 1):
        if check_remote_port_availability(ssh_conn, port):
            return port
    return None

def find_available_ports(ssh_conn) -> Tuple[int, int]:
    """
    Find available ports for both local and remote use.
    
    Args:
        ssh_conn: SSH connection object for remote port checking.
        
    Returns:
        A tuple of (local_port, remote_port) that are available.
    """
    local_port = find_available_port()
    if local_port is None:
        raise RuntimeError("No available local ports found")
    
    # Start remote search from the next port after the local port (or wrap-around)
    remote_start_port = local_port + 1 if local_port < 9000 else 8000
    remote_port = find_available_remote_port(ssh_conn, start_port=remote_start_port, end_port=9000)
    if remote_port is None:
        raise RuntimeError("No available remote ports found")
    
    return local_port, remote_port