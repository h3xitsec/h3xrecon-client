from .config import ClientConfig
from collections import defaultdict
from typing import Optional
from dataclasses import dataclass
from typing import Any
from loguru import logger
from typing import List, Dict, Any
import asyncio
import asyncpg

@dataclass
class DbResult:
    """Standardized return type for database operations"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None

    @property
    def failed(self) -> bool:
        return not self.success

class Database:
    def __init__(self):
        logger.debug("Initializing Database")
        self.config = ClientConfig().database.to_dict()
        self._initialize()
    
    def _initialize(self, config=None):
        # Initialize your database connection here
        logger.debug(f"Database config: {self.config}")
        self.pool = None

    async def __aenter__(self):
        await self.ensure_connected()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def ensure_connected(self):
        if self.pool is None:
            await self.connect()

    async def connect(self):
        self.pool = await asyncpg.create_pool(**self.config)

    async def close(self):
        if self.pool:
            await self.pool.close()
    
    async def _fetch_records(self, query: str, *args):
        """Execute a SELECT query and return the results."""
        try:
            await self.ensure_connected()
            async with self.pool.acquire() as conn:
                records = await conn.fetch(query, *args)
                formatted_records = await self.format_records(records)
            return DbResult(success=True, data=formatted_records)
        except Exception as e:
            return DbResult(success=False, error=str(e))
    
    async def _fetch_value(self, query: str, *args):
        """Execute a SELECT query and return the first value."""
        try:
            await self.ensure_connected()
            async with self.pool.acquire() as conn:
                value = await conn.fetchval(query, *args)
            return DbResult(success=True, data=value)
        except Exception as e:
            return DbResult(success=False, error=str(e))

    async def _write_records(self, query: str, *args):
        """Execute an INSERT, UPDATE, or DELETE query and return the outcome."""
        logger.debug(f"Executing modification query: {query} with args: {args}")
        return_data = DbResult(success=False, data=None, error=None)
        try:
            await self.ensure_connected()
            async with self.pool.acquire() as conn:
                if 'RETURNING' in query.upper():
                    records = await conn.fetch(query, *args)  # Directly use the acquired connection
                    formatted_records = await self.format_records(records)
                    if formatted_records:
                        return_data.success = True
                        return_data.data = formatted_records
                    else:
                        return_data.error = "No data returned from query."
                else:
                    result = await conn.execute(query, *args)
                    return_data.success = True
                    return_data.data = result
            return return_data
        except asyncpg.UniqueViolationError:
            return_data.error = "Unique violation error."
        except Exception as e:
            return_data.error = str(e)
        logger.debug(f"return_data: {return_data}")
        return return_data

    async def format_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes a list of database records and formats them for further processing
        
        Args:
            records: List of database record dictionaries
            
        Returns:
            List of formatted records with datetime objects converted to ISO format strings
            Empty list if error occurs
        """
            # Convert any datetime objects to strings for JSON serialization
        formatted_records = []
        for record in records:
            try:
                formatted_record = {}
                for key, value in record.items():
                    if hasattr(value, 'isoformat'):  # Check if datetime-like
                        formatted_record[key] = value.isoformat()
                    else:
                        formatted_record[key] = value
                formatted_records.append(formatted_record)
            except Exception as e:
                logger.error(f"Error formatting records: {str(e)}")
        return formatted_records