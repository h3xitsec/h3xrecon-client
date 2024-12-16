from loguru import logger
from typing import List
from .config import ClientConfig
from .database import Database
from .queue import ClientQueue
import redis
import asyncio
import time

class ClientAPI:
    def __init__(self):
        """
        Initialize the ClientAPI with a database connection.
        
        Sets up a database connection for performing various API operations.
        """
        logger.debug("Initializing ClientAPI")
        self.db = Database()
        self.queue = ClientQueue()
        self.redis_config = ClientConfig().redis
        self.redis_cache = redis.Redis(
            host=self.redis_config.host,
            port=self.redis_config.port,
            db=0,
            password=self.redis_config.password
        )
        self.redis_status = redis.Redis(
            host=self.redis_config.host,
            port=self.redis_config.port,
            db=1,
            password=self.redis_config.password
        )
    
    def get_workers(self):
        return self.redis_status.keys()
    
    def get_worker_status(self, worker_id: str):
        return self.redis_status.get(worker_id)
    
    

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
        return [{'key': key.decode(), 'value': self.redis_cache.get(key).decode()} for key in self.redis_cache.keys()]
        
    # Programs related methods
    async def get_programs(self):
        """
        Retrieve a list of all reconnaissance programs.
        
        Returns:
            A list of programs with their ID and name, ordered alphabetically.
        """
        query = """
        SELECT p.id, p.name
        FROM programs p
        ORDER BY p.name;
        """
        return await self.db._fetch_records(query)
    
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
        program_id = await self.get_program_id(program_name)
        query = """
        DELETE FROM domains WHERE program_id = $1
        """
        queries.append(query)
        query = """
        DELETE FROM urls WHERE program_id = $1
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
        for q in queries:
            await self.db._write_records(q, program_id)
    
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

    async def add_program_scope(self, program_name: str, scope: str):
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
        
        query = """
        INSERT INTO program_scopes (program_id, regex) VALUES ($1, $2)
        """
        return await self.db._write_records(query, program_id, scope)

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
        return await self.db._write_records(query, program_id, cidr)

    async def get_program_scope(self, program_name: str) -> List[str]:
        """
        Retrieve the scope regex patterns for a specific program.
        
        Args:
            program_name (str): The name of the program to retrieve scopes for.
        
        Returns:
            A list of regex patterns defining the program's scope.
        """
        query = """
        SELECT regex FROM program_scopes WHERE program_id = (SELECT id FROM programs WHERE name = $1)
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
        DELETE FROM program_scopes 
        WHERE program_id = (SELECT id FROM programs WHERE name = $1)
        AND regex = $2
        RETURNING id
        """
        result = await self.db._write_records(query, program_name, scope)
        if result:
            print(f"Scope removed from program {program_name}: {scope}")
            return True
        return False

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

    
    async def get_urls(self, program_name: str = None):
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
           u.url,
           u.title,
           u.status_code,
           u.content_type
        FROM urls u
        JOIN programs p ON u.program_id = p.id
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
        
        Args:
            program_name (str, optional): The name of the program to retrieve domains for.
                                          If None, retrieves domains from all programs.
        
        Returns:
            A list of domains associated with the specified program or all programs.
        """
        query = """
        SELECT 
            d.domain,
            (SELECT ip FROM ips WHERE id = ANY(d.ips) LIMIT 1) as resolved_ip,
            d.cnames,
            d.is_catchall,
            p.name as program
        FROM domains d
        JOIN programs p ON d.program_id = p.id
        """
        try:
            if program_name:
                query += """
                WHERE p.name = $1
                """
                result = await self.db._fetch_records(query, program_name)
            else:
                result = await self.db._fetch_records(query)
            return result
        except Exception as e:
            logger.exception(e)
            return []

    async def get_services(self, program_name: str = None):
        """
        Retrieve services for a specific program or all programs.
        
        Args:
            program_name (str, optional): The name of the program to retrieve services for.
                                          If None, retrieves services from all programs.
        
        Returns:
            A list of services associated with the specified program or all programs.
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
        JOIN ips i ON s.ip = i.id
        JOIN programs p ON s.program_id = p.id
        """
        try:
            if program_name:
                query += """
                WHERE p.name = $1
                """
                result = await self.db._fetch_records(query, program_name)
            else:
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
    
    async def add_item(self, item_type: str, program_name: str, items: list):
        """
        Add items (domains, IPs, or URLs) to a program through the queue.
        
        Args:
            item_type (str): Type of item to add (e.g., 'url', 'domain', 'ip').
            program_name (str): The name of the program to add items to.
            items (list): List of items to add.
        
        Prints an error message if the program is not found.
        """
        program_id = await self.get_program_id(program_name)
        if not program_id:
            print(f"Error: Program '{program_name}' not found")
            return

        # Format message based on item type
        if isinstance(items, str):
            items = [items]
        logger.debug(f"Adding {item_type} items to program {program_name}: {items}")
        if item_type == 'url':
            items = [{'url': item} for item in items]
        #for item in items:
        message = {
            "program_id": program_id,
            "data_type": item_type,
            "data": items
        }

        # For URLs, we need to format the data differently
        await self.queue.connect()
        await self.queue.publish_message(
            subject="recon.data",
            stream="RECON_DATA",
            message=message
        )
        await self.queue.close()

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
            subject="recon.data",
            stream="RECON_DATA",
            message=message
        )
        await self.queue.close()
        return True
    
    async def kill_job(self, worker_id: str):
        """
        Send a kill command to stop jobs on one or all workers.
        
        Args:
            worker_id (str): Specific worker ID or "all" to kill jobs on all workers
        """
        subscription = None
        try:
            if worker_id == "all":
                worker_keys = self.redis_status.keys("worker-*")
                worker_ids = [key.decode('utf-8') for key in worker_keys]
                print(f"Found {len(worker_ids)} workers to kill jobs for")
            else:
                worker_ids = [worker_id]

            # Connect once for all operations
            await self.queue.connect()
            
            # Send all kill commands first without waiting for responses
            for current_worker_id in worker_ids:
                control_message = {
                    "command": "killjob",
                    "target_worker_id": current_worker_id
                }
                
                await self.queue.publish_message(
                    subject="function.control",
                    stream="FUNCTION_CONTROL",
                    message=control_message
                )
                print(f"Sent kill command to worker {current_worker_id}")

            # Brief wait to allow messages to be sent
            await asyncio.sleep(0.5)

            # Check that all workers are idle
            max_retries = 10
            retry_count = 0
            while retry_count < max_retries:
                all_idle = True
                for current_worker_id in worker_ids:
                    status = self.get_worker_status(current_worker_id)
                    if status and status.decode('utf-8') != 'idle':
                        all_idle = False
                        break
                
                if all_idle:
                    print("All workers are now idle")
                    break
                    
                retry_count += 1
                await asyncio.sleep(1)
                
            if not all_idle:
                logger.warning("Some workers may still be processing jobs after kill command")
                
        except Exception as e:
            logger.error(f"Failed to send kill command(s): {e}")
            raise
        finally:
            # Force cleanup
            try:
                self.queue._running = False
                await self.queue.close()
                logger.debug("Queue connection closed")
            except Exception as e:
                logger.error(f"Error during queue cleanup: {e}")
    
    async def send_job(self, function_name: str, program_name: str, params: dict, force: bool):
        """
        Send a job to the worker using QueueManager.
        
        Args:
            function_name (str): The name of the function to execute.
            program_name (str): The name of the program associated with the job.
            params (dict): The parameters for the job.
            force (bool): Whether to force the job execution.
        
        Logs an error if the program does not exist.
        """
        try:
            program_id = await self.get_program_id(program_name)
        except Exception as e:
            logger.error(f"Non existent program '{program_name}'")
            logger.exception(e)
            return

        message = {
            "force": force,
            "function": function_name,
            "program_id": program_id,
            "params": params #{"target": target}
        }

        await self.queue.connect()
        await self.queue.publish_message(
            subject="function.execute",
            stream="FUNCTION_EXECUTE",
            message=message
        )
        await self.queue.close()
    
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