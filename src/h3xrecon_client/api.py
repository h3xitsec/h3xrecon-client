from typing import List, Dict, Any, Union, Optional
from .config import ClientConfig
from .database import Database, DatabaseConnectionError, DbResult
from .cache import Cache, CacheResult
from .queue import ClientQueue
import redis
import asyncio
import json
from nats.js.api import ConsumerConfig, DeliverPolicy, AckPolicy
import redis.exceptions
from loguru import logger

class ClientAPI:
    def __init__(self):
        """
        Initialize the ClientAPI with a database connection.
        
        Sets up a database connection for performing various API operations.
        """
        
        try:
            self.db = Database()
            self.queue = ClientQueue()
            self.redis_config = ClientConfig().redis
            
            # Initialize Redis connections with error handling
            try:
                self.redis_cache = Cache(type="cache")
                self.redis_status = Cache(type="status")
                # Test connections
                self.redis_cache.ping()
                self.redis_status.ping()
            except redis.exceptions.ConnectionError as e:
                logger.error(f"Redis connection failed: {str(e)}")
                self.redis_cache = None
                self.redis_status = None
            except redis.exceptions.AuthenticationError:
                logger.error("Redis authentication failed")
                self.redis_cache = None
                self.redis_status = None
            
        except DatabaseConnectionError as e:
            logger.error(f"Failed to initialize database connection: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize ClientAPI: {str(e)}")
            raise
    
    async def get_components(self, type: str):
        """Get components with Redis error handling."""
        try:
            if self.redis_status is None:
                return CacheResult(success=False, error="Redis connection not available")
            # Only get keys that start with 'worker-'
            all_keys = self.redis_status.keys()
            if type == "all":
                components = all_keys
            elif type in ["recon", "parsing", "data"]:
                components = [key for key in all_keys if key.startswith(type)]
            else:
                return CacheResult(success=False, error="Invalid component type")
            
            return CacheResult(success=True, data=components)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis error while getting components: {str(e)}")
            return CacheResult(success=False, error=str(e))
    
    async def get_component_status(self, component_id: str):
        """Get component status with Redis error handling."""
        try:
            if self.redis_status is None:
                return DbResult(success=False, error="Redis connection not available")
            status = self.redis_status.get(component_id)
            if status:
                status = status
            return DbResult(success=True, data=status)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis error while getting component status: {str(e)}")
            return DbResult(success=False, error=str(e))

    async def flush_component_status(self, component_id: str) -> DbResult:
        """Flush component status from Redis.
        
        Args:
            component_type (str): Type of component to flush ('worker', 'jobprocessor', 'dataprocessor', 'all')
            
        Returns:
            DbResult: Result of the flush operation
        """
        try:
            if self.redis_status is None:
                return CacheResult(success=False, error="Redis connection not available")
            self.redis_status.delete(component_id)
            return CacheResult(success=True)

        except redis.exceptions.RedisError as e:
            logger.error(f"Redis error while flushing component status: {str(e)}")
            return CacheResult(success=False, error=str(e))

    async def get_workers(self):
        """Get workers with Redis error handling."""
        try:
            if self.redis_status is None:
                return CacheResult(success=False, error="Redis connection not available")
            # Only get keys that start with 'worker-'
            prefix_bytes = b'worker-'
            all_keys = self.redis_status.keys()
            workers = [key.decode() for key in all_keys if key.startswith(prefix_bytes)]
            return CacheResult(success=True, data=workers)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis error while getting workers: {str(e)}")
            return CacheResult(success=False, error=str(e))
    
    async def get_worker_status(self, worker_id: str):
        """Get worker status with Redis error handling."""
        try:
            if self.redis_status is None:
                return DbResult(success=False, error="Redis connection not available")
            status = self.redis_status.get(worker_id)
            if status:
                status = status.decode()
            return DbResult(success=True, data=status)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis error while getting worker status: {str(e)}")
            return DbResult(success=False, error=str(e))
    
    async def get_processors(self, processor_type: str):
        """Get list of processors of specified type with Redis error handling.
        
        Args:
            processor_type (str): Type of processor ('jobprocessors' or 'dataprocessors')
        """
        try:
            if self.redis_status is None:
                return DbResult(success=False, error="Redis connection not available")
            
            # Convert plural to singular for the prefix and remove 's' if it exists
            prefix = processor_type.rstrip('s')
            # Add hyphen to ensure exact prefix match (e.g., 'jobprocessor-' not 'jobprocessorextra-')
            prefix = f"{prefix}-"
            prefix_bytes = prefix.encode()  # Convert prefix to bytes for comparison
            
            # Get all keys and filter for the ones that match our pattern
            all_keys = self.redis_status.keys()
            processors = [key.decode() for key in all_keys if key.startswith(prefix_bytes)]
            
            # Debug logging




            
            return DbResult(success=True, data=processors)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis error while getting processors: {str(e)}")
            return DbResult(success=False, error=str(e))

    async def get_processor_status(self, processor_id: str):
        """Get processor status with Redis error handling.
        
        Args:
            processor_id (str): ID of the processor to get status for
        """
        try:
            if self.redis_status is None:
                return DbResult(success=False, error="Redis connection not available")
            status = self.redis_status.get(processor_id)
            if status:
                status = status.decode()
            return DbResult(success=True, data=status)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis error while getting processor status: {str(e)}")
            return DbResult(success=False, error=str(e))

    async def flush_cache(self):
        """
        Flush the Redis cache.
        """
        self.redis_cache.flushdb()
    
    async def show_cache_keys(self):
        """
        Show the Redis cache info.
        """
        return self.redis_cache.keys()

    async def show_cache_keys_values(self):
        """
        Show the Redis cache keys with values
        """
        return [{'key': key, 'value': self.redis_cache.get(key)} for key in self.redis_cache.keys()]
        
    # Programs related methods
    async def get_programs(self):
        """
        Retrieve a list of all reconnaissance programs.
        
        Returns:
            DbResult: A result object containing the list of programs
        """
        try:
            query = """
            SELECT p.id, p.name
            FROM programs p
            ORDER BY p.name;
            """
            result = await self.db._fetch_records(query)
            if result.failed:
                logger.error(f"Failed to get programs: {result.error}")
                if "Database connection error" in str(result.error):
                    print("Error: Could not connect to database. Please check your database configuration and connectivity.")
                return DbResult(success=False, error=result.error)
            return result
        except Exception as e:
            logger.error(f"Unexpected error in get_programs: {str(e)}")
            return DbResult(success=False, error=str(e))
    
    async def get_program_id(self, program_name: str) -> int:
        """
        Retrieve the ID of a specific program by its name.
        
        Args:
            program_name (str): The name of the program to look up.
        
        Returns:
            int: The ID of the program, or None if not found.
        """
        query = """
        SELECT id FROM programs WHERE name = $1
        """
        result = await self.db._fetch_records(query, program_name)
        return result.data[0].get('id') if result.data else None

    async def drop_program_data(self, program_name: str):
        """
        Delete all data associated with a specific program.
        
        This method removes domains, URLs, services, and IPs linked to the program.
        
        Args:
            program_name (str): The name of the program whose data will be deleted.
        """
        queries = []
        try:
            program_id = await self.get_program_id(program_name)
            query = """
            DELETE FROM domains WHERE program_id = $1
            """
            queries.append(query)
            query = """
            DELETE FROM websites WHERE program_id = $1
            """
            queries.append(query)
            query = """
            DELETE FROM websites_paths WHERE program_id = $1
            """
            queries.append(query)
            query = """
            DELETE FROM services WHERE program_id = $1
            """
            queries.append(query)
            query = """
            DELETE FROM ips WHERE program_id = $1
            """
            queries.append(query)
            query = """
            DELETE FROM nuclei WHERE program_id = $1
            """
            queries.append(query)
            query = """
            DELETE FROM certificates WHERE program_id = $1
            """
            queries.append(query)
            query = """
            DELETE FROM screenshots WHERE program_id = $1
            """
            queries.append(query)
            for q in queries:
                await self.db._write_records(q, program_id)
            return DbResult(success=True)
        except Exception as e:
            logger.error(f"Unexpected error in drop_program_data: {str(e)}")
            return DbResult(success=False, error=str(e))
    
    async def add_program(self, name: str):
        """
        Add a new reconnaissance program to the database.
        
        Args:
            name (str): The name of the new program to be added.
        
        Returns:
            The result of the insert operation, including the new program's ID.
        """
        query = "INSERT INTO programs (name) VALUES ($1) RETURNING id"
        insert_result = await self.db._write_records(query, name)
        return insert_result

    async def remove_program(self, program_name: str):
        """
        Remove a program from the database.
        """
        query = "DELETE FROM programs WHERE name = $1"
        return await self.db._write_records(query, program_name)

    async def add_program_scope(self, program_name: str, domain: str, wildcard: bool = False, regex: Optional[str] = None):
        """
        Add a scope regex pattern to a specific program.
        
        Args:
            program_name (str): The name of the program to add the scope to.
            scope (str): The regex pattern defining the program's scope.
        
        Raises:
            ValueError: If the program is not found.
        
        Returns:
            The result of the insert operation.
        """
        program_id = await self.get_program_id(program_name)
        if program_id is None:
            raise ValueError(f"Program '{program_name}' not found")
        if wildcard:
            if regex:
                print(f"Warning: Wildcard and regex cannot be used together, regex will be ignored")
            _regex = f"^.*{domain.replace('.', '\\.')}$"
            _wildcard = True
        elif regex:
            _regex = regex
            if not _regex.startswith('^'):
                _regex = f"^{_regex}"
            if not _regex.endswith('$'):
                _regex = f"{_regex}$"
            _wildcard = True
        
        else:
            _regex = f"^{domain}$"
            _wildcard = False
        query = """
        INSERT INTO program_scopes_domains (program_id, domain, wildcard, regex) VALUES ($1, $2, $3, $4)
        ON CONFLICT (program_id, domain, regex) DO NOTHING
        RETURNING (xmax = 0) AS inserted, id
        """
        result = await self.db._write_records(query, program_id, domain, _wildcard, _regex)
        if result.success and isinstance(result.data, list) and len(result.data) > 0:
            return {
                'inserted': result.data[0]['inserted'],
                'id': result.data[0]['id']
            }
        return {'inserted': False, 'id': None}

    async def add_program_cidr(self, program_name: str, cidr: str):
        """
        Add a CIDR range to a specific program.
        
        Args:
            program_name (str): The name of the program to add the CIDR to.
            cidr (str): The CIDR range to be added.
        
        Raises:
            ValueError: If the program is not found.
        
        Returns:
            The result of the insert operation.
        """
        program_id = await self.get_program_id(program_name)
        if program_id is None:
            raise ValueError(f"Program '{program_name}' not found")
        
        query = """
        INSERT INTO program_cidrs (program_id, cidr) VALUES ($1, $2)
        """
        result = await self.db._write_records(query, program_id, cidr)
        if result.success and isinstance(result.data, list) and len(result.data) > 0:
            return {
                'inserted': result.data[0]['inserted'],
                'id': result.data[0]['id']
            }
        return {'inserted': False, 'id': None}

    async def get_program_scope(self, program_name: str) -> List[str]:
        """
        Retrieve the scope regex patterns for a specific program.
        
        Args:
            program_name (str): The name of the program to retrieve scopes for.
        
        Returns:
            A list of regex patterns defining the program's scope.
        """
        query = """
        SELECT domain,wildcard,regex FROM program_scopes_domains WHERE program_id = (SELECT id FROM programs WHERE name = $1)
        """
        result = await self.db._fetch_records(query, program_name)
        return result
    
    async def get_program_cidr(self, program_name: str) -> List[str]:
        """
        Retrieve the CIDR ranges for a specific program.
        
        Args:
            program_name (str): The name of the program to retrieve CIDR ranges for.
        
        Returns:
            A list of CIDR ranges associated with the program.
        """
        query = """
        SELECT cidr FROM program_cidrs WHERE program_id = (SELECT id FROM programs WHERE name = $1)
        """
        result = await self.db._fetch_records(query, program_name)
        return result
    
    async def remove_program_scope(self, program_name: str, scope: str):
        """
        Remove a specific scope regex pattern from a program.
        
        Args:
            program_name (str): The name of the program.
            scope (str): The regex pattern to remove.
        
        Returns:
            bool: True if the scope was successfully removed, False otherwise.
        """
        query = """
        DELETE FROM program_scopes_domains
        WHERE program_id = (SELECT id FROM programs WHERE name = $1)
        AND domain = $2
        RETURNING id
        """
        return await self.db._write_records(query, program_name, scope)

    async def remove_program_cidr(self, program_name: str, cidr: str):
        """
        Remove a specific CIDR range from a program.
        
        Args:
            program_name (str): The name of the program.
            cidr (str): The CIDR range to remove.
        
        Returns:
            bool: True if the CIDR was successfully removed, False otherwise.
        """
        query = """
        DELETE FROM program_cidrs 
        WHERE program_id = (SELECT id FROM programs WHERE name = $1)
        AND cidr = $2
        RETURNING id
        """
        result = await self.db._write_records(query, program_name, cidr)
        if result:
            print(f"CIDR removed from program {program_name}: {cidr}")
            return True
        return False

    async def remove_program_config(self, program_name: str, config_type: str, items: list):
        """
        Remove multiple scope or CIDR configurations from a program.
        
        Args:
            program_name (str): Name of the program.
            config_type (str): Type of config ('scope' or 'cidr').
            items (list): List of items to remove.
        
        Prints an error message if the program is not found.
        """
        program_id = await self.db.get_program_id(program_name)
        if not program_id:
            print(f"Error: Program '{program_name}' not found")
            return

        table_name = f"program_{config_type}"
        column_name = "pattern" if config_type == "scope" else "cidr"
        
        for item in items:
            query = f"""
            DELETE FROM {table_name}
            WHERE program_id = $1 AND {column_name} = $2
            """
            await self.db._write_records(query, program_id, item)


    # Assets related methods
    async def remove_domain(self, program_name: str, domain: str):
        """
        Remove a specific domain from a program.
        
        Args:
            program_name (str): The name of the program.
            domain (str): The domain to remove.
        
        Returns:
            bool: True if the domain was successfully removed, False otherwise.
        """
        query = """
        DELETE FROM domains 
        WHERE program_id = (SELECT id FROM programs WHERE name = $1)
        AND domain = $2
        RETURNING id
        """
        result = await self.db._fetch_value(query, program_name, domain)
        if result:
            print(f"Domain removed from program {program_name}: {domain}")
            return True
        return False

    
    async def get_websites(self, program_name: str = None):
        """
        Retrieve URLs for a specific program or all programs.
        
        Args:
            program_name (str, optional): The name of the program to retrieve URLs for.
                                          If None, retrieves URLs from all programs.
        
        Returns:
            A list of URLs associated with the specified program or all programs.
        """
        if program_name:
            query = """
        SELECT 
           w.url,
           w.host,
           w.port,
           w.scheme,
           w.techs
        FROM websites w
        JOIN programs p ON w.program_id = p.id
        WHERE p.name = $1
        """
            result = await self.db._fetch_records(query, program_name)
            return result
        
    async def get_websites_paths(self, program_name: str = None):
        """
        Retrieve websites paths for a specific program or all programs.
        """
        query = """
        SELECT 
            w.url || wp.path as url,
            wp.path,
            wp.final_path,
            wp.status_code,
            wp.content_type
        FROM websites_paths wp
        JOIN websites w ON wp.website_id = w.id
        JOIN programs p ON w.program_id = p.id
        WHERE p.name = $1
        """
        result = await self.db._fetch_records(query, program_name)
        return result

    async def get_resolved_domains(self, program_name: str = None):
        """
        Retrieve domains with their resolved IP addresses.
        
        Args:
            program_name (str, optional): The name of the program to retrieve resolved domains for.
                                          If None, retrieves resolved domains from all programs.
        
        Returns:
            A list of domains with their associated resolved IP addresses.
        """
        query = """
        SELECT 
            d.domain,
            array_agg(i.ip) as resolved_ips
        FROM domains d
        JOIN programs p ON d.program_id = p.id
        JOIN ips i ON i.id = ANY(d.ips)
        WHERE d.ips IS NOT NULL 
        AND array_length(d.ips, 1) > 0
        """
        if program_name:
            query += " AND p.name = $1 GROUP BY d.domain"
            result = await self.db._fetch_records(query, program_name)
        else:
            query += " GROUP BY d.domain"
            result = await self.db._fetch_records(query)
        return result

    async def get_unresolved_domains(self, program_name: str = None):
        """
        Retrieve domains without resolved IP addresses.
        
        Args:
            program_name (str, optional): The name of the program to retrieve unresolved domains for.
                                          If None, retrieves unresolved domains from all programs.
        
        Returns:
            A list of domains without resolved IP addresses.
        """
        query = """
        SELECT 
            d.*
        FROM domains d
        JOIN programs p ON d.program_id = p.id
        WHERE (d.ips IS NULL 
        OR array_length(d.ips, 1) = 0 
        OR d.ips = '{}')
        """
        if program_name:
            query += " AND p.name = $1"
            result = await self.db._fetch_records(query, program_name)
        else:
            result = await self.db._fetch_records(query)
        return result

    async def get_reverse_resolved_ips(self, program_name: str = None):
        """
        Retrieve IP addresses with reverse DNS resolution.
        
        Args:
            program_name (str, optional): The name of the program to retrieve reverse resolved IPs for.
                                          If None, retrieves reverse resolved IPs from all programs.
        
        Returns:
            A list of IP addresses with their reverse DNS names.
        """
        query = """
        SELECT 
            i.*
        FROM ips i
        JOIN programs p ON i.program_id = p.id
        WHERE i.ptr IS NOT NULL
        AND i.ptr != ''
        """
        if program_name:
            query += " AND p.name = $1"
            result = await self.db._fetch_records(query, program_name)
        else:
            result = await self.db._fetch_records(query)
        return result

    async def get_not_reverse_resolved_ips(self, program_name: str = None):
        """
        Retrieve IP addresses without reverse DNS resolution.
        
        Args:
            program_name (str, optional): The name of the program to retrieve non-reverse resolved IPs for.
                                          If None, retrieves non-reverse resolved IPs from all programs.
        
        Returns:
            A list of IP addresses without reverse DNS names.
        """
        query = """
        SELECT 
            i.*
        FROM ips i
        JOIN programs p ON i.program_id = p.id
        WHERE i.ptr IS NULL
        OR i.ptr = ''
        """
        if program_name:
            query += " AND p.name = $1"
            result = await self.db._fetch_records(query, program_name)
        else:
            result = await self.db._fetch_records(query)
        return result

    async def get_domains(self, program_name: str = None):
        """
        Retrieve domains for a specific program or all programs.
        """
        query = """
        SELECT 
            d.domain,
            array_agg(i.ip) as resolved_ips,
            d.cnames,
            d.is_catchall,
            p.name as program
        FROM domains d
        LEFT JOIN ips i ON i.id = ANY(d.ips)
        JOIN programs p ON d.program_id = p.id
        """
        try:
            if program_name:
                query += """
                WHERE p.name = $1
                """
                query += " GROUP BY d.domain, d.cnames, d.is_catchall, p.name"
                result = await self.db._fetch_records(query, program_name)
            else:
                query += " GROUP BY d.domain, d.cnames, d.is_catchall, p.name"
                result = await self.db._fetch_records(query)
            return result
        except Exception as e:
            logger.exception(e)
            return []
    
    async def get_screenshots(self, program_name: str = None):
        """
        Retrieve screenshots for a specific program or all programs.
        
        Args:
            program_name (str, optional): The name of the program to retrieve screenshots for.
                                          If None, retrieves screenshots from all programs.
        
        Returns:
            A list of screenshots associated with the specified program or all programs.
        """
        query = """
        SELECT 
            w.url,
            s.filepath,
            s.md5_hash
        FROM screenshots s
        JOIN websites w ON s.website_id = w.id
        JOIN programs p ON s.program_id = p.id
        """
        if program_name:
            query += " WHERE p.name = $1"
            result = await self.db._fetch_records(query, program_name)
        else:
            result = await self.db._fetch_records(query)
        return result

    async def get_services(self, program_name: str = None):
        """
        Retrieve services for a specific program or all programs.
        """
        query = """
        SELECT 
            s.protocol,
            i.ip,
            s.port,
            s.service,
            i.ptr,
            p.name as program_name
        FROM services s
        LEFT JOIN ips i ON i.id = s.ip
        JOIN programs p ON s.program_id = p.id
        """
        try:
            if program_name:
                query += """
                WHERE p.name = $1
                """
                query += " GROUP BY s.protocol, i.ip, s.port, s.service, i.ptr, p.name"
                result = await self.db._fetch_records(query, program_name)
            else:
                query += " GROUP BY s.protocol, i.ip, s.port, s.service, i.ptr, p.name"
                result = await self.db._fetch_records(query)
            return result
        except Exception as e:
            logger.exception(e)
            return []

    async def get_ips(self, program_name: str = None):
        """
        Retrieve IP addresses for a specific program or all programs.
        
        Args:
            program_name (str, optional): The name of the program to retrieve IP addresses for.
                                          If None, retrieves IP addresses from all programs.
        
        Returns:
            A list of IP addresses associated with the specified program or all programs.
        """
        try:
            query = """
            SELECT 
                ip,
                ptr,
                cloud_provider,
                p.name as program
            FROM ips i
            JOIN programs p ON i.program_id = p.id
            """
            if program_name:
                query += " WHERE p.name = $1"
                return await self.db._fetch_records(query, program_name)
            
            return await self.db._fetch_records(query)
        except Exception as e:
            logger.exception(e)
            return []
    
    async def get_nuclei(self, program_name: str = None, severity: str = None):
        """
        Retrieve nuclei results for a specific program or all programs.
        
        Args:
            program_name (str, optional): The name of the program to retrieve nuclei results for.
                                          If None, retrieves nuclei results from all programs.
            severity (str, optional): The severity of the nuclei results to retrieve.
                                          If None, retrieves nuclei results from all severities.
        
        Returns:
            A list of nuclei results associated with the specified program or all programs.
        """
        query = """
        SELECT 
            url, template_id, severity, matcher_name
        FROM nuclei n
        JOIN programs p ON n.program_id = p.id
        """
        if program_name:
            query += " WHERE p.name = $1"
        if severity:
            query += " AND severity = $2"
            result = await self.db._fetch_records(query, program_name, severity)
        else:
            result = await self.db._fetch_records(query, program_name)
        return result
    
    async def add_item(self, item_type: str, program_name: str, items: Union[str, List[str]]) -> DbResult:
        """
        Add items (domains, IPs, or URLs) to a program through the queue.
        
        Args:
            item_type (str): Type of item to add ('domain', 'ip', 'website')
            program_name (str): The name of the program to add items to
            items (Union[str, List[str]]): Single item or list of items to add
        
        Returns:
            DbResult: Result object with success status and optional error
        """
        try:
            # Get program ID
            program_id = await self.get_program_id(program_name)
            if not program_id:
                return DbResult(success=False, error=f"Program '{program_name}' not found")

            # Ensure items is a list
            if isinstance(items, str):
                items = [items]

            # Format items based on type
            formatted_items = []
            for item in items:
                if item_type == 'website':
                    formatted_items.append({'url': item})
                else:
                    formatted_items.append(item)

            # Prepare message
            message = {
                "program_id": program_id,
                "data_type": item_type,
                "data": formatted_items,
                "trigger_new_jobs": True,
                "execution_id": None
            }

            # Send through queue
            await self.queue.connect()
            try:
                await self.queue.publish_message(
                    subject="data.input",
                    stream="DATA_INPUT",
                    message=message
                )
                return DbResult(success=True)
            finally:
                await self.queue.close()

        except Exception as e:
            logger.error(f"Error adding {item_type}(s): {str(e)}")
            return DbResult(success=False, error=str(e))

    async def remove_item(self, item_type: str, program_name: str, item: str) -> bool:
        """
        Remove an item (domain, IP, or URL) from a program.
        
        Args:
            item_type (str): Type of item to remove (e.g., 'url', 'domain', 'ip').
            program_name (str): The name of the program to remove the item from.
            item (str): The specific item to remove.
        
        Returns:
            bool: True if the item was successfully removed, False otherwise.
        
        Prints an error message if the program is not found.
        """
        program_id = await self.db.get_program_id(program_name)
        if not program_id:
            print(f"Error: Program '{program_name}' not found")
            return False

        message = {
            "program_id": program_id,
            "data_type": item_type,
            "action": "delete",
            "data": [item]
        }

        await self.queue.connect()
        await self.queue.publish_message(
            subject="data.input",
            stream="DATA_INPUT",
            message=message
        )
        await self.queue.close()
        return True
    
    async def kill_job(self, target: str):
        """
        Send a kill command to stop jobs on one or all workers.
        
        Args:
            target (str): Specific component ID, "worker" for all workers, or "all" for all components
            
        Returns:
            Dict containing command status and responses from components
        """
        try:
            await self.queue.connect()
            
            # Ensure response stream exists
            try:
                await self.queue.js.stream_info("CONTROL_RESPONSE_KILLJOB")
            except Exception:
                await self.queue.js.add_stream(
                    name="CONTROL_RESPONSE_KILLJOB",
                    subjects=["control.response.killjob"]
                )

            # Create ephemeral subscription for responses
            response_sub = await self.queue.js.pull_subscribe(
                subject="control.response.killjob",
                durable=None,
                stream="CONTROL_RESPONSE_KILLJOB",
                config=ConsumerConfig(
                    deliver_policy=DeliverPolicy.NEW,
                    ack_policy=AckPolicy.EXPLICIT,
                    max_deliver=1
                )
            )

            # Send kill command
            control_message = {"command": "killjob"}
            
            # Determine subject based on target
            if target == "recon":
                subject = "worker.control.all_recon"
            elif target == "all":
                subject = "worker.control.all"
            else:
                subject = f"worker.control.{target}"

            await self.queue.publish_message(
                subject=subject,
                stream="WORKER_CONTROL",
                message=control_message
            )

            # Get expected components to wait for responses from
            if target == "all":
                expected_components = await self.get_components("all")
            elif target == "recon":
                expected_components = await self.get_components("recon")
            else:
                expected_components = DbResult(success=True, data=[target])

            if not expected_components.success:
                return {"status": "error", "message": "Failed to get component list"}

            # Wait for responses
            responses = []
            received_components = set()
            max_wait_time = 15  # seconds
            start_time = asyncio.get_event_loop().time()
            while len(received_components) < len(expected_components.data):
                if (asyncio.get_event_loop().time() - start_time) > max_wait_time:
                    break
                    
                try:
                    msgs = await response_sub.fetch(batch=10, timeout=1)
                    for msg in msgs:
                        try:
                            data = json.loads(msg.data.decode())
                            if data.get('component_id'):
                                responses.append(data)
                                received_components.add(data['component_id'])
                            await msg.ack()
                        except json.JSONDecodeError:
                            logger.error(f"Failed to decode message: {msg.data}")
                            await msg.ack()
                        
                except Exception as e:
                    if "timeout" not in str(e).lower():
                        logger.error(f"Error fetching messages: {e}")
                    await asyncio.sleep(0.1)
            missing_components = []
            # Get list of components that didn't respond
            for comp in expected_components.data:
                if comp not in received_components:
                    missing_components.append(comp)
            
            return {
                "status": "success" if responses else "warning",
                "message": f"Kill command sent to {target}",
                "responses": responses,
                "missing_responses": missing_components
            }

        except Exception as e:
            logger.error(f"Failed to send kill command: {e}")
            return {"status": "error", "message": str(e)}
            
        finally:
            # Clean up subscription
            if 'response_sub' in locals():
                try:
                    await response_sub.unsubscribe()
                except:
                    pass
            await self.queue.close()
    
    async def send_job(self, function_name: str, program_name: str, params: dict, force: bool, trigger_new_jobs: bool = True):
        """
        Send a job to the worker using QueueManager.
        
        Args:
            function_name (str): The name of the function to execute.
            program_name (str): The name of the program associated with the job.
            params (dict): The parameters for the job.
            force (bool): Whether to force the job execution.
        
        Returns:
            DbResult: A result object with success status and optional error message
        """
        try:
            program_id = await self.get_program_id(program_name)
            if not program_id:
                return DbResult(success=False, error=f"Program '{program_name}' not found")

            message = {
                "force": force,
                "function_name": function_name,
                "program_id": program_id,
                "params": params,
                "trigger_new_jobs": trigger_new_jobs
            }

            await self.queue.connect()
            await self.queue.publish_message(
                subject="recon.input",
                stream="RECON_INPUT",
                message=message
            )
            await self.queue.close()
            
            return DbResult(success=True)
            
        except Exception as e:
            logger.error(f"Error sending job: {str(e)}")
            return DbResult(success=False, error=str(e))

    
    async def get_certificates(self, program_name: str = None):
        """
        Retrieve certificates for a specific program or all programs.
        """
        query = """
        SELECT subject_cn, issuer_org, serial, valid_date, expiry_date, array_length(subject_an, 1) as subject_an_count 
        FROM certificates c
        JOIN programs p ON c.program_id = p.id
        """
        if program_name:
            query += " WHERE p.name = $1"
        return await self.db._fetch_records(query, program_name)

    async def _wait_for_responses(self, response_sub, timeout: int = 5) -> List[Dict[str, Any]]:
        """
        Helper method to wait for responses from components.
        
        Args:
            response_sub: NATS subscription to receive responses
            timeout: Maximum time to wait for responses in seconds
            
        Returns:
            List of response messages received
        """
        responses = []
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                msgs = await response_sub.fetch(batch=1, timeout=1)
                for msg in msgs:
                    try:
                        data = json.loads(msg.data.decode())
                        responses.append(data)
                        await msg.ack()
                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode message: {msg.data}")
                        await msg.ack()
                        
                # If we got responses, we can break early
                if responses:
                    break
                    
            except Exception as e:
                if "timeout" not in str(e).lower():
                    logger.error(f"Error fetching messages: {e}")
                await asyncio.sleep(0.1)
                
        return responses
    
    async def pause_component(self, component: str, disable: bool = False) -> Dict[str, Any]:
        """
        Unpause a specific component.
        
        Args:
            component_id: ID of the component to unpause
        """
        try:
            expected_components = await self.get_components(component)
            await self.queue.connect()
            if disable:
                action = "unpause"
            else:
                action = "pause"
            try:
                await self.queue.js.stream_info(f"CONTROL_RESPONSE_{action.upper()}")
            except Exception:
                #print(f"Creating CONTROL_RESPONSE_{action.upper()} stream...")
                await self.queue.js.add_stream(name=f"CONTROL_RESPONSE_{action.upper()}",
                                                subjects=[f"control.response.{action}"])
            
            # Create subscription for responses
            response_sub = await self.queue.js.pull_subscribe(
                subject=f"control.response.{action}",
                durable=None,
                stream=f"CONTROL_RESPONSE_{action.upper()}",
                config=ConsumerConfig(
                    deliver_policy=DeliverPolicy.NEW,
                    ack_policy=AckPolicy.EXPLICIT,
                    max_deliver=1
                )
            )
            
            # Send unpause command
            control_message = {"command": action}
            
            # Determine subject based on target
            if component == "recon" or component == "parsing" or component == "data":
                subject = f"worker.control.all_{component}"
            elif component == "all":
                subject = "worker.control.all"
            else:
                subject = f"worker.control.{component}"
            
            await self.queue.publish_message(
                subject=subject,
                stream="WORKER_CONTROL",
                message=control_message
            )
            
            # Wait for responses
            responses = []
            received_components = set()
            max_wait_time = 15
            start_time = asyncio.get_event_loop().time()
            
            while len(received_components) < len(expected_components.data):
                if (asyncio.get_event_loop().time() - start_time) > max_wait_time:
                    break
                    
                try:
                    msgs = await response_sub.fetch(batch=10, timeout=1)
                    for msg in msgs:
                        try:
                            data = json.loads(msg.data.decode())
                            if data.get('component_id') and 'success' in data:
                                responses.append(data)
                                received_components.add(data['component_id'])
                            await msg.ack()
                        except json.JSONDecodeError:
                            logger.error(f"Failed to decode message: {msg.data}")
                            await msg.ack()
                        
                except Exception as e:
                    if "timeout" not in str(e).lower():
                        logger.error(f"Error fetching messages: {e}")
                        logger.exception(e)
                    await asyncio.sleep(0.1)
            # Get list of components that didn't respond
            missing_components = []

            for c in expected_components.data:
                #comp = c.decode() if isinstance(c, bytes) else c
                if c not in received_components:
                    missing_components.append(c)
            
            return {
                "status": "success" if responses else "warning",
                "message": f"{action.capitalize()} command sent to {component}",
                "responses": responses,
                "missing_responses": missing_components
            }
            
        except Exception as e:
            logger.error(f"Failed to send unpause command: {e}")
            logger.exception(e)
            
            return {"status": "error", "message": str(e)}
        finally:
            if 'response_sub' in locals():
                try:
                    await response_sub.unsubscribe()
                except:
                    pass
            await self.queue.close()
    
    async def get_component_report(self, component_id: str = None) -> Dict[str, Any]:
        """
        Get a report from a specific component or all components of a type.
        """
        try:
            await self.queue.connect()
            
            # Ensure response stream exists
            try:
                await self.queue.js.stream_info("CONTROL_RESPONSE_REPORT")
            except Exception:
                await self.queue.js.add_stream(
                    name="CONTROL_RESPONSE_REPORT",
                    subjects=["control.response.report"]
                )

            # Create ephemeral subscription for responses
            response_sub = await self.queue.js.pull_subscribe(
                subject="control.response.report",
                durable=None,
                stream="CONTROL_RESPONSE_REPORT",
                config=ConsumerConfig(
                    deliver_policy=DeliverPolicy.NEW,
                    ack_policy=AckPolicy.EXPLICIT,
                    max_deliver=1
                )
            )
            
            # Send the report request
            control_message = {
                "command": "report",
                "target": component_id
            }
            if component_id == 'all':
                subject = f"worker.control.all_{component_id}"
            else:
                control_message["target_worker_id"] = component_id
                subject = f"worker.control.{component_id}"            
            await self.queue.publish_message(
                subject=subject,
                stream="WORKER_CONTROL",
                message=control_message
            )

            await self.queue.publish_message(
                subject=subject,
                stream="WORKER_CONTROL",
                message=control_message
            )
            
            # Wait a bit for the message to be processed
            await asyncio.sleep(0.5)
            
            # Wait for responses (with timeout)
            responses = []
            start_time = asyncio.get_event_loop().time()
            timeout = 5  # 5 seconds timeout
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    msgs = await response_sub.fetch(batch=1, timeout=1)
                    for msg in msgs:
                        try:
                            data = json.loads(msg.data.decode())
                            if data.get('command') == 'report':
                                responses.append(data)
                            await msg.ack()
                        except json.JSONDecodeError:
                            logger.error(f"Failed to decode message: {msg.data}")
                            await msg.ack()
                    
                    # If we got responses, we can break early
                    if responses:
                        break
                    
                except Exception as e:
                    if "timeout" not in str(e).lower():
                        logger.error(f"Error fetching messages: {e}")
                    # Don't break on timeout, continue until full timeout period
                    await asyncio.sleep(0.1)
                        
            if not responses:
                return {"status": "error", "message": f"No response received from {component_id} after {timeout} seconds"}
            
            return {"status": "success", "reports": responses}
            
        except Exception as e:
            logger.error(f"Failed to get report: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            # Clean up subscription
            if 'response_sub' in locals():
                try:
                    await response_sub.unsubscribe()
                except:
                    pass
            await self.queue.close()

    async def ping_component(self, component_id: str) -> Dict[str, Any]:
        """
        Send a ping to a specific component and wait for pong response.
        
        Args:
            component_id: ID of the component to ping
        """
        try:
            # Ensure streams exist
            await self.queue.connect()
            try:
                await self.queue.js.stream_info("CONTROL_RESPONSE_PING")
            except Exception as e:
                # Create stream if it doesn't exist
                #print("Creating CONTROL_RESPONSE_PING stream...")
                await self.queue.js.add_stream(name="CONTROL_RESPONSE_PING",
                                             subjects=["control.response.ping"])
            
            
            # Create a subscription for responses before sending command
            response_sub = await self.queue.js.pull_subscribe(
                subject="control.response.ping",
                durable=None,  # Ephemeral consumer
                stream="CONTROL_RESPONSE_PING",
                config=ConsumerConfig(
                    deliver_policy=DeliverPolicy.NEW,
                    ack_policy=AckPolicy.EXPLICIT,
                    max_deliver=1
                )
            )
            
            # Send the ping request
            control_message = {
                "command": "ping",
            }
            
            await self.queue.publish_message(
                subject=f"worker.control.{component_id}",
                stream="WORKER_CONTROL",
                message=control_message
            )
            
            # Wait a bit for the message to be processed
            await asyncio.sleep(0.1)
            responses = await self._wait_for_responses(response_sub)
            
            return {
                "status": "success" if responses else "warning",
                "message": f"Ping command sent to {component_id}",
                "responses": responses
            }
            
        except Exception as e:
            logger.error(f"Failed to ping component: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            # Clean up subscription
            if 'response_sub' in locals():
                try:
                    await response_sub.unsubscribe()
                except:
                    pass
            await self.queue.close()

    async def backup_database(self, backup_path: str) -> DbResult:
        """
        Backup the entire database to a file.
        
        Args:
            backup_path (str): Path where the backup file will be saved
            
        Returns:
            DbResult: Result of the backup operation
        """
        try:
            # Ensure database connection is established
            await self.db.ensure_connected()
            
            async with self.db.pool.acquire() as conn:
                with open(backup_path, 'w') as f:
                    # First get and write all sequences
                    sequences = await conn.fetch("""
                        SELECT sequence_name 
                        FROM information_schema.sequences 
                        WHERE sequence_schema = 'public'
                        ORDER BY sequence_name
                    """)
                    
                    f.write("-- Sequences\n")
                    for seq in sequences:
                        seq_name = seq['sequence_name']
                        # Get sequence current value
                        curr_val = await conn.fetchval(f"SELECT last_value FROM {seq_name}")
                        f.write(f"DROP SEQUENCE IF EXISTS {seq_name} CASCADE;\n")
                        f.write(f"CREATE SEQUENCE {seq_name};\n")
                        if curr_val > 1:  # Only set if not default
                            f.write(f"SELECT setval('{seq_name}', {curr_val}, true);\n")
                    f.write("\n")
                    
                    # Get all tables
                    tables = await conn.fetch("""
                        SELECT tablename 
                        FROM pg_tables 
                        WHERE schemaname = 'public'
                        ORDER BY tablename
                    """)
                    
                    # Get column types for all tables
                    table_column_types = {}
                    for table in tables:
                        table_name = table['tablename']
                        column_types = await conn.fetch("""
                            SELECT column_name, data_type, udt_name
                            FROM information_schema.columns
                            WHERE table_name = $1
                        """, table_name)
                        table_column_types[table_name] = {
                            col['column_name']: col['udt_name']
                            for col in column_types
                        }
                    
                    # First get and write all table schemas
                    for table in tables:
                        table_name = table['tablename']
                        
                        # Get complete table schema including constraints
                        schema = await conn.fetch(f"""
                            SELECT 
                                a.attname as column_name,
                                pg_catalog.format_type(a.atttypid, a.atttypmod) as data_type,
                                a.attnotnull as is_notnull,
                                (SELECT pg_get_expr(adbin, adrelid)
                                 FROM pg_attrdef
                                 WHERE adrelid = a.attrelid
                                 AND adnum = a.attnum) as column_default
                            FROM pg_attribute a
                            WHERE a.attrelid = '{table_name}'::regclass
                            AND a.attnum > 0
                            AND NOT a.attisdropped
                            ORDER BY a.attnum;
                        """)
                        
                        # Get primary key info
                        pkey = await conn.fetch(f"""
                            SELECT a.attname
                            FROM pg_index i
                            JOIN pg_attribute a ON a.attrelid = i.indrelid
                            AND a.attnum = ANY(i.indkey)
                            WHERE i.indrelid = '{table_name}'::regclass
                            AND i.indisprimary;
                        """)
                        
                        # Get foreign key constraints
                        fkeys = await conn.fetch(f"""
                            SELECT
                                tc.constraint_name,
                                kcu.column_name,
                                ccu.table_name AS foreign_table_name,
                                ccu.column_name AS foreign_column_name
                            FROM information_schema.table_constraints AS tc
                            JOIN information_schema.key_column_usage AS kcu
                                ON tc.constraint_name = kcu.constraint_name
                            JOIN information_schema.constraint_column_usage AS ccu
                                ON ccu.constraint_name = tc.constraint_name
                            WHERE tc.table_name = '{table_name}'
                                AND tc.constraint_type = 'FOREIGN KEY';
                        """)
                        
                        # Write table creation
                        f.write(f"-- Table: {table_name}\n")
                        f.write(f"DROP TABLE IF EXISTS {table_name} CASCADE;\n")
                        f.write(f"CREATE TABLE {table_name} (\n")
                        
                        # Write columns
                        columns = []
                        for col in schema:
                            col_def = []
                            col_def.append(f"    {col['column_name']} {col['data_type']}")
                            
                            if col['is_notnull']:
                                col_def.append('NOT NULL')
                            if col['column_default']:
                                col_def.append(f"DEFAULT {col['column_default']}")
                            
                            columns.append(" ".join(col_def))
                        
                        # Add primary key constraint if exists
                        if pkey:
                            pkey_cols = [pk['attname'] for pk in pkey]
                            columns.append(f"    PRIMARY KEY ({', '.join(pkey_cols)})")
                        
                        f.write(",\n".join(columns))
                        f.write("\n);\n\n")
                        
                        # Write foreign key constraints
                        for fkey in fkeys:
                            f.write(f"ALTER TABLE {table_name} ADD CONSTRAINT {fkey['constraint_name']} \n")
                            f.write(f"    FOREIGN KEY ({fkey['column_name']}) \n")
                            f.write(f"    REFERENCES {fkey['foreign_table_name']}({fkey['foreign_column_name']});\n")
                        if fkeys:
                            f.write("\n")
                    
                    # Then write all table data
                    for table in tables:
                        table_name = table['tablename']
                        column_types = table_column_types[table_name]
                        records = await conn.fetch(f"SELECT * FROM {table_name}")
                        
                        if records:
                            f.write(f"-- Data for {table_name}\n")
                            for record in records:
                                columns = [k for k in record.keys()]
                                values = []
                                for col, v in zip(columns, record.values()):
                                    if v is None:
                                        values.append('NULL')
                                    elif isinstance(v, (list, tuple)):
                                        # Handle array types with proper casting
                                        base_type = column_types[col].replace('_', '')  # Remove array indicator
                                        if all(x is None for x in v):
                                            # If all elements are NULL, use empty array with type cast
                                            values.append(f"ARRAY[]::integer[]" if base_type in ('int2', 'int4', 'int8', 'integer') else f"ARRAY[]::varchar[]")
                                        else:
                                            array_values = []
                                            for x in v:
                                                if x is None:
                                                    array_values.append('NULL')
                                                elif base_type in ('int2', 'int4', 'int8', 'integer'):
                                                    array_values.append(str(x))
                                                else:
                                                    array_values.append(f"'{str(x)}'")
                                            # Use proper array type casting
                                            array_type = "integer[]" if base_type in ('int2', 'int4', 'int8', 'integer') else "varchar[]"
                                            values.append(f"ARRAY[{', '.join(array_values)}]::{array_type}")
                                    elif isinstance(v, bool):
                                        values.append(str(v))
                                    else:
                                        values.append(f"'{str(v).replace(chr(39), chr(39)+chr(39))}'")
                                
                                f.write(f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
                            f.write("\n")
                
                return DbResult(success=True)
                
        except Exception as e:
            logger.error(f"Database backup failed: {str(e)}")
            return DbResult(success=False, error=str(e))

    async def restore_database(self, backup_path: str) -> DbResult:
        """
        Restore the database from a backup file.
        
        Args:
            backup_path (str): Path to the backup file
            
        Returns:
            DbResult: Result of the restore operation
        """
        try:
            # Ensure database connection is established
            await self.db.ensure_connected()
            
            async with self.db.pool.acquire() as conn:
                # First disable foreign key constraints
                await conn.execute('SET CONSTRAINTS ALL DEFERRED;')
                
                # Read and execute the backup file
                with open(backup_path, 'r') as f:
                    sql_commands = []
                    current_command = []
                    
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('--'):  # Skip comments and empty lines
                            current_command.append(line)
                            if line.endswith(';'):
                                sql_commands.append('\n'.join(current_command))
                                current_command = []
                    
                    # Execute each command in a transaction
                    async with conn.transaction():
                        for command in sql_commands:
                            try:
                                await conn.execute(command)
                            except Exception as e:
                                logger.error(f"Error executing command: {str(e)}\nCommand: {command}")
                                return DbResult(success=False, error=f"Restore failed: {str(e)}")
                
                # Re-enable constraints
                await conn.execute('SET CONSTRAINTS ALL IMMEDIATE;')
                return DbResult(success=True)
                
        except Exception as e:
            logger.error(f"Database restore failed: {str(e)}")
            return DbResult(success=False, error=str(e))
