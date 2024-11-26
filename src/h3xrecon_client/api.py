from loguru import logger
from typing import List
from .config import ClientConfig
from .database import Database

class ClientAPI:
    def __init__(self):
        logger.debug("Initializing ClientAPI")
        self.db = Database()

    # Programs related methods
    async def get_programs(self):
        """List all reconnaissance programs"""
        query = """
        SELECT p.id, p.name
        FROM programs p
        ORDER BY p.name;
        """
        return await self.db._fetch_records(query)
    
    async def get_program_id(self, program_name: str) -> int:
        query = """
        SELECT id FROM programs WHERE name = $1
        """
        result = await self.db._fetch_records(query, program_name)
        return result.data[0].get('id',{})

    async def drop_program_data(self, program_name: str):
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

        for q in queries:
            await self.db._write_records(q, program_id)
    
    async def add_program(self, name: str):
        """Add a new program to the database"""
        query = "INSERT INTO programs (name) VALUES ($1) RETURNING id"
        insert_result = await self.db._write_records(query, name)
        return insert_result

    async def get_programs(self):
        """List all reconnaissance programs"""
        query = """
        SELECT p.id, p.name
        FROM programs p
        ORDER BY p.name;
        """
        return await self.db._fetch_records(query)
    
    async def add_program_scope(self, program_name: str, scope: str):
        program_id = await self.get_program_id(program_name)
        if program_id is None:
            raise ValueError(f"Program '{program_name}' not found")
        
        query = """
        INSERT INTO program_scopes (program_id, regex) VALUES ($1, $2)
        """
        return await self.db._write_records(query, program_id, scope)

    async def add_program_cidr(self, program_name: str, cidr: str):
        program_id = await self.get_program_id(program_name)
        if program_id is None:
            raise ValueError(f"Program '{program_name}' not found")
        
        query = """
        INSERT INTO program_cidrs (program_id, cidr) VALUES ($1, $2)
        """
        return await self.db._write_records(query, program_id, cidr)

    async def get_program_scope(self, program_name: str) -> List[str]:
        query = """
        SELECT regex FROM program_scopes WHERE program_id = (SELECT id FROM programs WHERE name = $1)
        """
        result = await self.db._fetch_records(query, program_name)
        return result
    
    async def get_program_cidr(self, program_name: str) -> List[str]:
        query = """
        SELECT cidr FROM program_cidrs WHERE program_id = (SELECT id FROM programs WHERE name = $1)
        """
        result = await self.db._fetch_records(query, program_name)
        return result
    
    async def remove_program_scope(self, program_name: str, scope: str):
        """Remove a specific scope regex from a program"""
        query = """
        DELETE FROM program_scopes 
        WHERE program_id = (SELECT id FROM programs WHERE name = $1)
        AND regex = $2
        RETURNING id
        """
        result = await self.db._write_records(query, program_name, scope)
        if result:
            logger.info(f"Scope removed from program {program_name}: {scope}")
            return True
        return False

    async def remove_program_cidr(self, program_name: str, cidr: str):
        """Remove a specific CIDR from a program"""
        query = """
        DELETE FROM program_cidrs 
        WHERE program_id = (SELECT id FROM programs WHERE name = $1)
        AND cidr = $2
        RETURNING id
        """
        result = await self.db._write_records(query, program_name, cidr)
        if result:
            logger.info(f"CIDR removed from program {program_name}: {cidr}")
            return True
        return False

    async def remove_program_config(self, program_name: str, config_type: str, items: list):
        """Remove scope or CIDR configuration from a program
        Args:
            program_name (str): Name of the program
            config_type (str): Type of config ('scope' or 'cidr')
            items (list): List of items to remove
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
        """Remove a specific domain from a program"""
        query = """
        DELETE FROM domains 
        WHERE program_id = (SELECT id FROM programs WHERE name = $1)
        AND domain = $2
        RETURNING id
        """
        result = await self.db._fetch_value(query, program_name, domain)
        if result:
            logger.info(f"Domain removed from program {program_name}: {domain}")
            return True
        return False

    
    async def get_urls(self, program_name: str = None):
        if program_name:
            query = """
        SELECT 
           *
        FROM urls u
        JOIN programs p ON u.program_id = p.id
        WHERE p.name = $1
        """
            result = await self.db._fetch_records(query, program_name)
            return result
    
    async def get_urls_details(self, program_name: str = None):
        """Get details about URLs in a program"""
        if program_name:
            query = """
            SELECT 
                u.url, 
                httpx_data->>'title' as title,
                httpx_data->>'status_code' as status_code,
                httpx_data->>'tech' as technologies,
                httpx_data->>'body_preview' as body_preview,
                p.name as program_name
            FROM urls u
            JOIN programs p ON u.program_id = p.id
            WHERE p.name = $1
            """
            return await self.db._fetch_records(query, program_name)

    async def get_resolved_domains(self, program_name: str = None):
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
        query = """
        SELECT 
            *
        FROM domains d
        JOIN programs p ON d.program_id = p.id
        """
        if program_name:
            query += """
            WHERE p.name = $1
            """
            result = await self.db._fetch_records(query, program_name)
        else:
            result = await self.db._fetch(query)
        return result

    async def get_services(self, program_name: str = None):
        query = """
        SELECT 
            *,
            p.name as program_name
        FROM services s
        JOIN ips i ON s.ip = i.id
        JOIN programs p ON s.program_id = p.id
        """
        if program_name:
            query += """
            WHERE p.name = $1
            """
            result = await self.db._fetch_records(query, program_name)
        else:
            result = await self.db._fetch_records(query)
        return result

    async def get_ips(self, program_name: str = None):
        if program_name:
            query = """
            SELECT 
                *
            FROM ips i
            JOIN programs p ON i.program_id = p.id
            WHERE p.name = $1
            """
            result = await self.db._fetch_records(query, program_name)
            return result
    
    async def add_item(self, item_type: str, program_name: str, items: list):
        """Add items (domains, IPs, or URLs) to a program through the queue"""
        program_id = await self.db.get_program_id(program_name)
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
        await self.qm.connect()
        await self.qm.publish_message(
            subject="recon.data",
            stream="RECON_DATA",
            message=message
        )
        await self.qm.close()

    async def remove_item(self, item_type: str, program_name: str, item: str) -> bool:
        """Remove an item (domain, IP, or URL) from a program"""
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

        await self.qm.connect()
        await self.qm.publish_message(
            subject="recon.data",
            stream="RECON_DATA",
            message=message
        )
        await self.qm.close()
        return True

    async def send_job(self, function_name: str, program_name: str, target: str, force: bool):
        """Send a job to the worker using QueueManager"""
        try:
            program_id = await self.db.get_program_id(program_name)
        except Exception as e:
            logger.error(f"Non existent program '{program_name}'")
            return

        message = {
            "force": force,
            "function": function_name,
            "program_id": program_id,
            "params": {"target": target}
        }

        await self.qm.connect()
        await self.qm.publish_message(
            subject="function.execute",
            stream="FUNCTION_EXECUTE",
            message=message
        )
        await self.qm.close()