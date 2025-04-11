# load_balancer.py
import random
import time
from typing import Dict, Any, List, Optional

class LoadBalancer:
    def __init__(self, deployment_manager):
        self.deployment_manager = deployment_manager
        self.strategy = "round_robin"  # Could be 'round_robin', 'random', 'least_connections'
        self.current_index = 0
        self.connection_counts = {}  # For least_connections strategy
        
    def get_endpoint_for_request(self, request_data=None) -> Optional[str]:
        """Get the next endpoint to send a request to"""
        endpoints = self.deployment_manager.get_active_endpoints()
        
        if not endpoints:
            return None
            
        # default to using round_robin 
        endpoint = self._round_robin_select(endpoints)
        if self.strategy == "random":
            endpoint = self._random_select(endpoints)
        elif self.strategy == "least_connections":
            endpoint = self._least_connections_select(endpoints)
        return endpoint["endpoint"]
        
    def _round_robin_select(self, endpoints: List[Dict]) -> Dict:
        """Select an endpoint using round-robin strategy"""
        endpoint = endpoints[self.current_index % len(endpoints)]
        self.current_index += 1
        return endpoint
        
    def _random_select(self, endpoints: List[Dict]) -> Dict:
        """Select an endpoint randomly"""
        return random.choice(endpoints)
        
    def _least_connections_select(self, endpoints: List[Dict]) -> Dict:
        """Select the endpoint with the least active connections"""
        # Initialize connection counts for new endpoints
        for endpoint in endpoints:
            instance_id = endpoint["instance_id"]
            if instance_id not in self.connection_counts:
                self.connection_counts[instance_id] = 0
                
        # Clean up old endpoints
        for instance_id in list(self.connection_counts.keys()):
            if instance_id not in [e["instance_id"] for e in endpoints]:
                del self.connection_counts[instance_id]
                
        # Find endpoint with least connections
        min_connections = float('inf')
        selected_endpoint = None
        
        for endpoint in endpoints:
            instance_id = endpoint["instance_id"]
            if self.connection_counts[instance_id] < min_connections:
                min_connections = self.connection_counts[instance_id]
                selected_endpoint = endpoint
                
        # Increment connection count
        self.connection_counts[selected_endpoint["instance_id"]] += 1
        
        return selected_endpoint
        
    def release_endpoint(self, instance_id: str):
        """Mark an endpoint as no longer in use (for least_connections strategy)"""
        if instance_id in self.connection_counts:
            self.connection_counts[instance_id] = max(0, self.connection_counts[instance_id] - 1)