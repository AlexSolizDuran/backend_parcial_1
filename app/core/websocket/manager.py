from fastapi import WebSocket
from typing import Dict, List, Set
import json
import asyncio
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manage WebSocket connections for real-time notifications"""
    
    def __init__(self):
        # Dictionary to store active connections by taller_id
        # taller_id -> Set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = defaultdict(set)
        
        # Dictionary to store connection info for broadcasting
        # websocket -> {taller_id, user_id}
        self.connection_info: Dict[WebSocket, dict] = {}
    
    async def connect(self, websocket: WebSocket, taller_id: int = None, user_id: int = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        if taller_id:
            self.active_connections[taller_id].add(websocket)
            self.connection_info[websocket] = {
                "taller_id": taller_id,
                "user_id": user_id,
                "connected_at": asyncio.get_event_loop().time()
            }
            logger.info(f"WebSocket connected for taller_id: {taller_id}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        info = self.connection_info.pop(websocket, {})
        taller_id = info.get("taller_id")
        
        if taller_id and taller_id in self.active_connections:
            self.active_connections[taller_id].discard(websocket)
            # Clean up empty sets
            if not self.active_connections[taller_id]:
                del self.active_connections[taller_id]
            
            logger.info(f"WebSocket disconnected for taller_id: {taller_id}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def send_to_taller(self, message: dict, taller_id: int):
        """Send a message to all connections for a specific taller"""
        if taller_id not in self.active_connections:
            return
        
        disconnected = set()
        
        for connection in self.active_connections[taller_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to taller {taller_id}: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def notify_nearby_talleres(self, message: dict, taller_ids: List[int]):
        """Send a notification to multiple talleres"""
        for taller_id in taller_ids:
            await self.send_to_taller(message, taller_id)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all connected clients"""
        all_connections = set()
        for connections in self.active_connections.values():
            all_connections.update(connections)
        
        disconnected = set()
        
        for connection in all_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")
                disconnected.add(connection)
        
        for connection in disconnected:
            self.disconnect(connection)


# Global WebSocket manager instance
ws_manager = WebSocketManager()


async def websocket_endpoint(websocket: WebSocket, taller_id: int = None):
    """WebSocket endpoint for real-time communication"""
    await ws_manager.connect(websocket, taller_id=taller_id)
    
    try:
        while True:
            # Keep the connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                # Handle different message types
                message_type = message.get("type")
                
                if message_type == "ping":
                    await ws_manager.send_personal_message(
                        {"type": "pong", "timestamp": asyncio.get_event_loop().time()},
                        websocket
                    )
                elif message_type == "subscribe":
                    # Subscribe to specific channel
                    new_taller_id = message.get("taller_id")
                    if new_taller_id:
                        # Remove from old taller if any
                        old_info = ws_manager.connection_info.get(websocket, {})
                        old_taller_id = old_info.get("taller_id")
                        
                        if old_taller_id:
                            ws_manager.active_connections[old_taller_id].discard(websocket)
                        
                        # Add to new taller
                        ws_manager.active_connections[new_taller_id].add(websocket)
                        ws_manager.connection_info[websocket]["taller_id"] = new_taller_id
                        
                        await ws_manager.send_personal_message(
                            {"type": "subscribed", "taller_id": new_taller_id},
                            websocket
                        )
                            
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {data}")
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        ws_manager.disconnect(websocket)