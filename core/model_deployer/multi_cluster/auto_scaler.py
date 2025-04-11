import time
import threading
from queue_manager import RequestQueue

class AutoScaler:
    def __init__(self, 
                 request_queue,
                 deployment_manager,
                 min_replicas=1,
                 max_replicas=10,
                 scale_up_threshold=5,
                 scale_down_threshold=2,
                 cooldown_period=60):
        self.request_queue = request_queue
        self.deployment_manager = deployment_manager
        self.min_replicas = min_replicas
        self.max_replicas = max_replicas
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.cooldown_period = cooldown_period
        self.last_scale_time = 0
        self.current_replicas = min_replicas
        self.running = False
        self.monitor_thread = None
        
    def start_monitoring(self, check_interval=10):
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(check_interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
            
    def _monitor_loop(self, check_interval):
        while self.running:
            queue_length = self.request_queue.get_queue_length()
            self._make_scaling_decision(queue_length)
            time.sleep(check_interval)
            
    def _make_scaling_decision(self, queue_length):
        current_time = time.time()
        
        if current_time - self.last_scale_time < self.cooldown_period:
            return
            
        requests_per_replica = queue_length / max(1, self.current_replicas)
        if requests_per_replica > self.scale_up_threshold and self.current_replicas < self.max_replicas:
            target_replicas = min(
                self.max_replicas,
                self.current_replicas + max(1, int(queue_length / self.scale_up_threshold) - self.current_replicas)
            )
            self._scale_up(target_replicas)
            
        elif requests_per_replica < self.scale_down_threshold and self.current_replicas > self.min_replicas:
            target_replicas = max(
                self.min_replicas,
                min(self.current_replicas, int(queue_length / self.scale_down_threshold) + 1)
            )
            self._scale_down(target_replicas)
    
    def _scale_up(self, target_replicas):
        if target_replicas <= self.current_replicas:
            return
            
        print(f"Scaling up from {self.current_replicas} to {target_replicas} replicas")
        self.deployment_manager.scale_deployment(target_replicas)
        self.current_replicas = target_replicas
        self.last_scale_time = time.time()
        
    def _scale_down(self, target_replicas):
        if target_replicas >= self.current_replicas:
            return
            
        print(f"Scaling down from {self.current_replicas} to {target_replicas} replicas")
        self.deployment_manager.scale_deployment(target_replicas)
        self.current_replicas = target_replicas
        self.last_scale_time = time.time()