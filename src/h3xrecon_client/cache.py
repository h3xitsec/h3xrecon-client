import redis
from h3xrecon_client.config import ClientConfig
from typing import Optional, Any
from dataclasses import dataclass

@dataclass
class CacheResult:
    """Standardized return type for cache operations"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None

    @property
    def failed(self) -> bool:
        return not self.success

class Cache:
    def __init__(self, type: str = "status"):
        self.redis_config = ClientConfig().redis
        self.redis_cache = redis.Redis(
            host=self.redis_config.host,
            port=self.redis_config.port,
            db=1 if type == "status" else 0,
            password=self.redis_config.password,
        )

    def get(self, key):
        return self.redis_cache.get(key)

    def set(self, key, value):
        self.redis_cache.set(key, value)
    
    def ping(self):
        return self.redis_cache.ping()
    
    def keys(self):
        return self.redis_cache.keys()

    def flushdb(self):
        self.redis_cache.flushdb()

    def delete(self, key):
        """Delete a key from Redis.
        
        Args:
            key: The key to delete
        """
        return self.redis_cache.delete(key)
