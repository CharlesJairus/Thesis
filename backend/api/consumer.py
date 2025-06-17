import json
from  channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async,sync_to_async

#import models

class NotifConsumer(AsyncJsonWebsocketConsumer):
    
    async def connect(self):
    
        await self.channel_layer.group_add("notification", self.channel_name)
        
        await self.accept()
        
    async def receive(self, text_data):
        pass
       
    
    async def disconnect(self, code):
        await self.channel_layer.group_discard("notification",self.channel_name)
        
        self.close(code)
