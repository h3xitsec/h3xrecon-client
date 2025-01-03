import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
@dataclass
class RedisConfig:
    host: str
    port: int
    db: int
    password: Optional[str] = None

@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    min_size: int = 10
    max_size: int = 20

    def to_dict(self) -> Dict[str, Any]:
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password,
            'min_size': self.min_size,
            'max_size': self.max_size,
        }

@dataclass
class NatsConfig:
    host: str
    port: int
    user: Optional[str] = None
    password: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'password': self.password,
        }

    @property
    def url(self) -> str:
        if self.user and self.password:
            return f"nats://{self.user}:{self.password}@{self.host}:{self.port}"
        return f"nats://{self.host}:{self.port}"

@dataclass
class LogConfig:
    level: str
    format: str
    file_path: Optional[str] = None

class ClientConfig:
    def __init__(self):
        config = self._load_client_config_file()
        self.database = DatabaseConfig(**config.get('database', {}))
        self.nats = NatsConfig(**config.get('nats', {}))
        self.logging = LogConfig(**config.get('logging', {}))
        self.redis = RedisConfig(**config.get('redis', {}))
    
    def _load_client_config_file(self):
        """Load configuration from a JSON file."""
        config_path = os.path.expanduser('~/.h3xrecon/config.json')
        
        try:
            with open(config_path, 'r') as f:
                client_config_json = json.load(f)

            return client_config_json

        except FileNotFoundError:
            return None
        except Exception:
            return None