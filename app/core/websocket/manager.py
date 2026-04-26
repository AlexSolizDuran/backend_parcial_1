from fastapi import WebSocket
from typing import Dict, List, Set
import json
import asyncio
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = defaultdict(set)
        self.client_connections: Dict[int, Set[WebSocket]] = defaultdict(set)
        self.tecnico_connections: Dict[int, Set[WebSocket]] = defaultdict(set)
        self.connection_info: Dict[WebSocket, dict] = {}
    
    async def connect(self, websocket: WebSocket, taller_id: int = None, user_id: int = None, cliente_id: int = None, tecnico_id: int = None):
        logger.info(f"WS connect called: taller_id={taller_id}, user_id={user_id}, cliente_id={cliente_id}, tecnico_id={tecnico_id}")
        
        if taller_id:
            self.active_connections[taller_id].add(websocket)
            self.connection_info[websocket] = {
                "taller_id": taller_id,
                "user_id": user_id,
                "tipo": "taller",
                "connected_at": asyncio.get_event_loop().time()
            }
            logger.info(f"WebSocket connected for taller_id: {taller_id}")
        
        if cliente_id:
            self.client_connections[cliente_id].add(websocket)
            self.connection_info[websocket] = {
                "cliente_id": cliente_id,
                "tipo": "cliente",
                "connected_at": asyncio.get_event_loop().time()
            }
            logger.info(f"WebSocket connected for cliente_id: {cliente_id}")
        
        if tecnico_id:
            self.tecnico_connections[tecnico_id].add(websocket)
            self.connection_info[websocket] = {
                "tecnico_id": tecnico_id,
                "tipo": "tecnico",
                "connected_at": asyncio.get_event_loop().time()
            }
            logger.info(f"WebSocket connected for tecnico_id: {tecnico_id}")
    
    def disconnect(self, websocket: WebSocket):
        info = self.connection_info.pop(websocket, {})
        tipo = info.get("tipo")
        
        if tipo == "taller":
            taller_id = info.get("taller_id")
            if taller_id and taller_id in self.active_connections:
                self.active_connections[taller_id].discard(websocket)
                if not self.active_connections[taller_id]:
                    del self.active_connections[taller_id]
                logger.info(f"WebSocket disconnected for taller_id: {taller_id}")
        
        elif tipo == "cliente":
            cliente_id = info.get("cliente_id")
            if cliente_id and cliente_id in self.client_connections:
                self.client_connections[cliente_id].discard(websocket)
                if not self.client_connections[cliente_id]:
                    del self.client_connections[cliente_id]
                logger.info(f"WebSocket disconnected for cliente_id: {cliente_id}")
        
        elif tipo == "tecnico":
            tecnico_id = info.get("tecnico_id")
            if tecnico_id and tecnico_id in self.tecnico_connections:
                self.tecnico_connections[tecnico_id].discard(websocket)
                if not self.tecnico_connections[tecnico_id]:
                    del self.tecnico_connections[tecnico_id]
                logger.info(f"WebSocket disconnected for tecnico_id: {tecnico_id}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def send_to_taller(self, message: dict, taller_id: int):
        if taller_id not in self.active_connections:
            return
        
        disconnected = set()
        
        for connection in self.active_connections[taller_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to taller {taller_id}: {e}")
                disconnected.add(connection)
        
        for connection in disconnected:
            self.disconnect(connection)
    
    async def send_to_cliente(self, message: dict, cliente_id: int):
        if cliente_id not in self.client_connections:
            logger.info(f"No WebSocket connection for cliente_id: {cliente_id}")
            return
        
        disconnected = set()
        
        for connection in self.client_connections[cliente_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to cliente {cliente_id}: {e}")
                disconnected.add(connection)
        
        for connection in disconnected:
            self.disconnect(connection)
    
    async def send_to_tecnico(self, message: dict, tecnico_id: int):
        if tecnico_id not in self.tecnico_connections:
            logger.info(f"No WebSocket connection for tecnico_id: {tecnico_id}")
            return
        
        disconnected = set()
        
        for connection in self.tecnico_connections[tecnico_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to tecnico {tecnico_id}: {e}")
                disconnected.add(connection)
        
        for connection in disconnected:
            self.disconnect(connection)
    
    async def notify_nearby_talleres(self, message: dict, taller_ids: List[int]):
        for taller_id in taller_ids:
            await self.send_to_taller(message, taller_id)
    
    async def broadcast_to_all(self, message: dict):
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


ws_manager = WebSocketManager()


async def websocket_endpoint(websocket: WebSocket, taller_id: int = None, cliente_id: int = None, tecnico_id: int = None):
    await ws_manager.connect(websocket, taller_id=taller_id, cliente_id=cliente_id, tecnico_id=tecnico_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "ping":
                    await ws_manager.send_personal_message(
                        {"type": "pong", "timestamp": asyncio.get_event_loop().time()},
                        websocket
                    )
                elif message_type == "subscribe":
                    info = ws_manager.connection_info.get(websocket, {})
                    tipo = info.get("tipo")
                    
                    if tipo == "taller":
                        new_taller_id = message.get("taller_id")
                        if new_taller_id:
                            old_info = ws_manager.connection_info.get(websocket, {})
                            old_taller_id = old_info.get("taller_id")
                            
                            if old_taller_id:
                                ws_manager.active_connections[old_taller_id].discard(websocket)
                            
                            ws_manager.active_connections[new_taller_id].add(websocket)
                            ws_manager.connection_info[websocket]["taller_id"] = new_taller_id
                            
                            await ws_manager.send_personal_message(
                                {"type": "subscribed", "taller_id": new_taller_id},
                                websocket
                            )
                    
                elif message_type == "subscribe_cliente":
                    new_cliente_id = message.get("cliente_id")
                    if new_cliente_id:
                        old_info = ws_manager.connection_info.get(websocket, {})
                        old_cliente_id = old_info.get("cliente_id")
                        
                        if old_cliente_id:
                            ws_manager.client_connections[old_cliente_id].discard(websocket)
                        
                        ws_manager.client_connections[new_cliente_id].add(websocket)
                        ws_manager.connection_info[websocket]["cliente_id"] = new_cliente_id
                        ws_manager.connection_info[websocket]["tipo"] = "cliente"
                        
                        await ws_manager.send_personal_message(
                            {"type": "subscribed_cliente", "cliente_id": new_cliente_id},
                            websocket
                        )
                
                elif message_type == "subscribe_tecnico":
                    new_tecnico_id = message.get("tecnico_id")
                    if new_tecnico_id:
                        old_info = ws_manager.connection_info.get(websocket, {})
                        old_tecnico_id = old_info.get("tecnico_id")
                        
                        if old_tecnico_id:
                            ws_manager.tecnico_connections[old_tecnico_id].discard(websocket)
                        
                        ws_manager.tecnico_connections[new_tecnico_id].add(websocket)
                        ws_manager.connection_info[websocket]["tecnico_id"] = new_tecnico_id
                        ws_manager.connection_info[websocket]["tipo"] = "tecnico"
                        
                        await ws_manager.send_personal_message(
                            {"type": "subscribed_tecnico", "tecnico_id": new_tecnico_id},
                            websocket
                        )
                    
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {data}")
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        ws_manager.disconnect(websocket)