import os
import subprocess
import json
from core.model_deployer.profiler.commands import (
    OS_COMMANDS, 
    SUPPORTED_LINUX_DISTROS
)
from core.common.ssh import SSHConfig, SSH 
from core.common.logger import Logger 


logger = Logger(__name__, log_level="INFO", console_output=True)

class Profiler: 
    def __init__(self, ssh_config: SSHConfig = None):
        self.is_remote = ssh_config is not None
        self.conn = SSH.connect(ssh_config) if ssh_config else None 

    def _run_command(self, command: str) -> tuple[str, str]: 
        if self.is_remote: 
            return self._run_remote_command(command)
        return self._run_local_command(command)

    def _run_remote_command(self, command: str) -> tuple[str, str]:
        try:
            _, stdout, stderr = self.conn.exec_command(command)
            return stdout.read().decode('utf-8').strip(), stderr.read().decode('utf-8').strip()
        except Exception as e:
            print(f"Remote command error: {e}")
            return None, None
    
    def _run_local_command(self, command: str) -> tuple[str, str]: 
        try:
            result = subprocess.run(
                command,
                shell=True,
                text=True,
                capture_output=True,
                check=False 
            )
            return result.stdout.strip(), result.stderr.strip()
        except subprocess.SubprocessError as e:
            print(f"Local command error: {e}") 
            return None, None
    
    def _infer_os(self) -> str: 
        out, _ = self._run_command("uname -s")
        if out:
            if out == "Darwin":
                return "mac_os"
            elif out == "Linux":
                out, _ = self._run_command("cat /etc/os-release | grep ^ID=")
                if out:
                    distro = out.split('=')[1].strip('"')
                    if distro in SUPPORTED_LINUX_DISTROS:
                        return distro
            else:
                raise NotImplemented(f"Unsupported linux distro: {out}")

        out, _ = self._run_command("systeminfo")
        if out and "Windows" in out:
            return "windows"
        
        raise NotImplemented("Can't infer OS.")
    
    def _verify_environment(self):
        def verify_local_env(): 
            logger.info("Verifying local environment.")
            for tool in ["docker", "rsync"]:
                cmd = f"command -v {tool}"
                out, error = self._run_local_command(cmd)
                if error: 
                    logger.error(f"{tool} is not installed. Please install {tool} and try again.")
                    raise EnvironmentError(f"{tool} is not installed. Please install {tool} and try again.")

        def verify_remote_env(): 
            logger.info("Verifying remote environment.")
            for tool in ["docker", "sudo"]:
                cmd = f"command -v {tool}"
                out, error = self._run_remote_command(cmd)
                if error: 
                    logger.error(f"{tool} is not installed. Please install {tool} and try again.")
                    raise EnvironmentError(f"{tool} is not installed. Please install {tool} and try again.")
        
        verify_local_env() 
        if self.is_remote: 
            verify_remote_env() 
        logger.info("Remote environment verification complete.")
        
    def profile(self) -> dict[str, str]: 
        self._verify_environment()

        os_id = self._infer_os()
        if os_id not in OS_COMMANDS.keys(): 
            raise NotImplemented(f"We currently do not support {os_id}.")

        info = {'os': os_id}
        info.update({desc: self._run_command(command)[0] for desc, command in OS_COMMANDS[os_id].items()})

        # Write info to internal .json file
        profile_path = os.path.expanduser("~/prof.json")
        with open(profile_path, "w") as f:
            json.dump(info, f)
        
        self.conn.close()
        return info
