"""
Block (Square) MCP Server Client
Handles communication with the Block MCP server for POS operations
"""
import json
import subprocess
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from config.config_models import BlockMCPConfig
from utils.logger import get_logger


logger = get_logger(__name__)


class BlockMCPClient:
    """
    Client for interacting with Block MCP server
    Supports operations like updating catalog item prices, querying orders, etc.
    """
    
    def __init__(self, config: BlockMCPConfig, client_name: str = "block_mcp_client"):
        self.config = config
        self.client_name = client_name
        self.process = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize connection to MCP server"""
        if self.initialized:
            logger.info(f"[{self.client_name}] Already initialized")
            return
        
        try:
            logger.info(f"[{self.client_name}] Starting MCP server...")
            
            # Set environment variable for Square access token
            env = {
                "SQUARE_ACCESS_TOKEN": self.config.access_token,
                "SQUARE_ENVIRONMENT": self.config.environment
            }
            
            # Start MCP server process
            self.process = await asyncio.create_subprocess_exec(
                self.config.server_command,
                *self.config.server_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            self.initialized = True
            logger.info(f"[{self.client_name}] MCP server started successfully")
            
        except Exception as e:
            logger.error(f"[{self.client_name}] Failed to initialize MCP server: {e}")
            raise
    
    async def close(self):
        """Close connection to MCP server"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.initialized = False
            logger.info(f"[{self.client_name}] MCP server connection closed")
    
    async def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request to the MCP server"""
        if not self.initialized:
            await self.initialize()
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        try:
            # Send request
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()
            
            # Read response
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=self.config.timeout
            )
            
            response = json.loads(response_line.decode())
            
            if "error" in response:
                raise Exception(f"MCP error: {response['error']}")
            
            return response.get("result", {})
            
        except asyncio.TimeoutError:
            logger.error(f"[{self.client_name}] Request timeout for method: {method}")
            raise
        except Exception as e:
            logger.error(f"[{self.client_name}] Request failed: {e}")
            raise
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available MCP tools"""
        logger.info(f"[{self.client_name}] Listing available tools")
        
        try:
            result = await self._send_request("tools/list", {})
            return {
                "success": True,
                "tools": result.get("tools", []),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def update_catalog_item_price(
        self,
        item_id: str,
        new_price: float,
        currency: str = "USD",
        version: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update the price of a catalog item
        
        Args:
            item_id: Square catalog item ID
            new_price: New price in smallest currency unit (e.g., cents)
            currency: Currency code (default: USD)
            version: Optional item version for optimistic concurrency
            
        Returns:
            Result of the price update operation
        """
        logger.info(f"[{self.client_name}] Updating price for item {item_id} to {new_price}")
        
        params = {
            "name": "update_catalog_object",
            "arguments": {
                "object": {
                    "type": "ITEM_VARIATION",
                    "id": item_id,
                    "item_variation_data": {
                        "price_money": {
                            "amount": int(new_price * 100),  # Convert to cents
                            "currency": currency
                        }
                    },
                    "version": version
                }
            }
        }
        
        try:
            result = await self._send_request("tools/call", params)
            
            return {
                "success": True,
                "item_id": item_id,
                "new_price": new_price,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"[{self.client_name}] Failed to update price: {e}")
            return {
                "success": False,
                "item_id": item_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_catalog_item(self, item_id: str) -> Dict[str, Any]:
        """
        Retrieve a catalog item by ID
        
        Args:
            item_id: Square catalog item ID
            
        Returns:
            Catalog item details
        """
        logger.info(f"[{self.client_name}] Retrieving catalog item {item_id}")
        
        params = {
            "name": "retrieve_catalog_object",
            "arguments": {
                "object_id": item_id
            }
        }
        
        try:
            result = await self._send_request("tools/call", params)
            
            return {
                "success": True,
                "item": result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"[{self.client_name}] Failed to retrieve item: {e}")
            return {
                "success": False,
                "item_id": item_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def search_catalog_items(
        self,
        query: Optional[str] = None,
        item_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search catalog items
        
        Args:
            query: Search query string
            item_types: Filter by item types (e.g., ["ITEM"])
            
        Returns:
            List of matching catalog items
        """
        logger.info(f"[{self.client_name}] Searching catalog items: {query}")
        
        params = {
            "name": "search_catalog_objects",
            "arguments": {
                "object_types": item_types or ["ITEM"],
                "query": {
                    "text_query": {
                        "keywords": [query] if query else []
                    }
                } if query else {}
            }
        }
        
        try:
            result = await self._send_request("tools/call", params)
            
            return {
                "success": True,
                "items": result.get("objects", []),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"[{self.client_name}] Failed to search catalog: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def list_locations(self) -> Dict[str, Any]:
        """List all Square locations"""
        logger.info(f"[{self.client_name}] Listing locations")
        
        params = {
            "name": "list_locations",
            "arguments": {}
        }
        
        try:
            result = await self._send_request("tools/call", params)
            
            return {
                "success": True,
                "locations": result.get("locations", []),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"[{self.client_name}] Failed to list locations: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def search_orders(
        self,
        location_ids: List[str],
        query: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search orders with specific criteria
        
        Args:
            location_ids: List of location IDs to search
            query: Search query parameters
            
        Returns:
            List of matching orders
        """
        logger.info(f"[{self.client_name}] Searching orders for locations: {location_ids}")
        
        params = {
            "name": "search_orders",
            "arguments": {
                "location_ids": location_ids,
                "query": query or {}
            }
        }
        
        try:
            result = await self._send_request("tools/call", params)
            
            return {
                "success": True,
                "orders": result.get("orders", []),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"[{self.client_name}] Failed to search orders: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def batch_update_prices(
        self,
        price_updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Batch update multiple item prices
        
        Args:
            price_updates: List of updates with format:
                [{"item_id": "...", "new_price": 10.99, "currency": "USD"}, ...]
        
        Returns:
            Results of batch update operation
        """
        logger.info(f"[{self.client_name}] Batch updating {len(price_updates)} prices")
        
        results = []
        errors = []
        
        for update in price_updates:
            try:
                result = await self.update_catalog_item_price(
                    item_id=update["item_id"],
                    new_price=update["new_price"],
                    currency=update.get("currency", "USD"),
                    version=update.get("version")
                )
                
                if result["success"]:
                    results.append(result)
                else:
                    errors.append(result)
                    
            except Exception as e:
                errors.append({
                    "item_id": update.get("item_id"),
                    "error": str(e)
                })
        
        return {
            "success": len(errors) == 0,
            "updated_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors,
            "timestamp": datetime.now().isoformat()
        }


class BlockMCPClientSync:
    """Synchronous wrapper for BlockMCPClient"""
    
    def __init__(self, config: BlockMCPConfig):
        self.async_client = BlockMCPClient(config)
        self.loop = None
    
    def _get_loop(self):
        """Get or create event loop"""
        if self.loop is None:
            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
        return self.loop
    
    def _run_async(self, coro):
        """Run async coroutine synchronously"""
        loop = self._get_loop()
        return loop.run_until_complete(coro)
    
    def initialize(self):
        """Initialize connection"""
        return self._run_async(self.async_client.initialize())
    
    def close(self):
        """Close connection"""
        return self._run_async(self.async_client.close())
    
    def update_catalog_item_price(self, item_id: str, new_price: float, currency: str = "USD", version: Optional[int] = None):
        """Update catalog item price (sync)"""
        return self._run_async(
            self.async_client.update_catalog_item_price(item_id, new_price, currency, version)
        )
    
    def get_catalog_item(self, item_id: str):
        """Get catalog item (sync)"""
        return self._run_async(self.async_client.get_catalog_item(item_id))
    
    def search_catalog_items(self, query: Optional[str] = None, item_types: Optional[List[str]] = None):
        """Search catalog items (sync)"""
        return self._run_async(self.async_client.search_catalog_items(query, item_types))
    
    def list_locations(self):
        """List locations (sync)"""
        return self._run_async(self.async_client.list_locations())
    
    def search_orders(self, location_ids: List[str], query: Optional[Dict[str, Any]] = None):
        """Search orders (sync)"""
        return self._run_async(self.async_client.search_orders(location_ids, query))
    
    def batch_update_prices(self, price_updates: List[Dict[str, Any]]):
        """Batch update prices (sync)"""
        return self._run_async(self.async_client.batch_update_prices(price_updates))