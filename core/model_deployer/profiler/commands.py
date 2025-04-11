"""
Set of all shell commands for hardware profiler. 
Currently supporting: macos, windows, ubuntu/linux
"""

"""
Currently supports: 
    1. Linux (several distros, with nvidia gpus)
    2. MacOS 
    3. Windows 
"""


SUPPORTED_LINUX_DISTROS = ["ubuntu", "centos", "red hat", "debian", "linux"]

COMMAND_PIPELINES = {
    "linux": {
        "kernel_name": "uname -s", 
        "machine": "uname -m",
        "cpu_count": "nproc",  
        "memory_total": "free -g | grep \"Mem\" | awk \'{print $2}\'",
        "has_gpus": "nvidia-smi -L | wc -l",
        "gpu_count": "nvidia-smi --query-gpu=gpu_name --format=csv,noheader | wc -l",
        "gpu_info": "nvidia-smi --query-gpu=gpu_name --format=csv",
        "free_disk_space": "df -h | grep \"/$\" | awk \'{print substr($4, 1, length($4)-1)}\'"
    }, 
    "mac_os": {
        "kernel_name": "uname -s", 
        "machine": "uname -m",
        "cpu_count": "sysctl -n hw.ncpu",
        "memory_total": "sysctl -n hw.memsize",
        "gpu_info": "system_profiler SPDisplaysDataType",
        "free_disk_space": "df -h | grep -w \"/System/Volumes/Data$\" | awk \'{print $4}\'",
    }, 
    # TODO: test these window commands!
    "windows": {
        "kernel_name": "uname -s", 
        "machine": "uname -m",
        "cpu_count": "wmic cpu get NumberOfLogicalProcessors",
        "memory_total": "wmic computersystem get TotalPhysicalMemory",
        "gpu_info": "wmic path win32_VideoController get Name,AdapterRAM",
        "free_disk_space": "df -h | grep -w \"/System/Volumes/Data$\" | awk \'{print $4}\'",
    }
}

OS_COMMANDS = {
    distro: COMMAND_PIPELINES["linux"] for distro in SUPPORTED_LINUX_DISTROS
}
OS_COMMANDS.update({
    "mac_os": COMMAND_PIPELINES["mac_os"],
    "windows": COMMAND_PIPELINES["windows"],
})