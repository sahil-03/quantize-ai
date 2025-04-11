import redis
import json
import time
import uuid

class RequestQueue:
    def __init__(self, redis_host='localhost', redis_port=6379, queue_name='model_requests'):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port)
        self.queue_name = queue_name
        
    def enqueue_request(self, request_data):
        """Add a request to the queue"""
        request_id = str(uuid.uuid4())
        request_item = {
            'id': request_id,
            'data': request_data,
            'timestamp': time.time()
        }
        self.redis_client.lpush(self.queue_name, json.dumps(request_item))
        return request_id
        
    def dequeue_request(self):
        """Remove and return a request from the queue"""
        request = self.redis_client.rpop(self.queue_name)
        if request:
            return json.loads(request)
        return None
        
    def get_queue_length(self):
        """Get the current length of the queue"""
        return self.redis_client.llen(self.queue_name)