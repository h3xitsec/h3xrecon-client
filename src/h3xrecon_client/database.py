from .config import ClientConfig
from collections import defaultdict
from typing import Optional
from dataclasses import dataclass
from typing import Any
from loguru import logger
from typing import List, Dict, Any
import asyncio
import asyncpg
import asyncpg.exceptions
from typing import Union

@dataclass
class DbResult:
    """Standardized return type for database operations"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None

    @property
    def failed(self) -> bool:
        return not self.success

class DatabaseConnectionError(Exception):
    """Raised when the database connection cannot be established."""
    pass

class Database:
    def __init__(self):
        
        self.config = ClientConfig().database.to_dict()
        self._initialize()
    
    def _initialize(self, config=None):
        # Initialize your database connection here
        
        self.pool = None

    async def __aenter__(self):
        await self.ensure_connected()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def ensure_connected(self):
        """Ensure database connection with error handling."""
        if self.pool is None:
            try:
                await self.connect()
            except DatabaseConnectionError as e:
                logger.error(f"Database connection failed: {str(e)}")
                raise

    async def connect(self):
        """Establish connection to database with proper error handling."""
        try:
            self.pool = await asyncpg.create_pool(**self.config)
        except asyncpg.exceptions.InvalidPasswordError:
            raise DatabaseConnectionError("Invalid database credentials")
        except asyncpg.exceptions.InvalidCatalogNameError:
            raise DatabaseConnectionError("Database does not exist")
        except asyncpg.exceptions.CannotConnectNowError:
            raise DatabaseConnectionError("Database is not accepting connections")
        except asyncpg.exceptions.PostgresConnectionError as e:
            raise DatabaseConnectionError(f"Could not connect to database: {str(e)}")
        except Exception as e:
            raise DatabaseConnectionError(f"Unexpected database error: {str(e)}")

    async def close(self):
        if self.pool:
            await self.pool.close()
    
    async def _fetch_records(self, query: str, *args) -> DbResult:
        """Execute a SELECT query with enhanced error handling."""
        try:
            await self.ensure_connected()
            async with self.pool.acquire() as conn:
                records = await conn.fetch(query, *args)
                formatted_records = await self.format_records(records)
            return DbResult(success=True, data=formatted_records)
        except DatabaseConnectionError as e:
            return DbResult(success=False, error=f"Database connection error: {str(e)}")
        except asyncpg.exceptions.PostgresError as e:
            return DbResult(success=False, error=f"Database query error: {str(e)}")
        except Exception as e:
            return DbResult(success=False, error=f"Unexpected error: {str(e)}")
    
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