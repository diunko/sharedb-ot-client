import time
import logging
import json
import asyncio

# import httpx
import ssl

import websockets
from websockets.client import WebSocketClientProtocol

from typing import Optional
from dataclasses import dataclass

from delta import Delta


# from composer.capi_client.protocol.generic.protocol import (
#     Client as CapiCliProto,
#     Server as CapiSrvProto
# )
# from composer.capi_client.protocol.unified import (
#     Client as ClientProto,
#     Server as ServerProto)
# from composer.capi_client.document import ClientDoc, AlertDelta


@dataclass
class BaseClientSession:
    pass


@dataclass
class ClientSession:
    conn: WebSocketClientProtocol = None

    sent_rev: int = 0
    sid: int = -1
    _id: int = -1

    def __post_init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    async def recv(self):
        try:
            msg_str = await self.conn.recv()
            # self.log.debug('client got raw message: %s', msg_str)
            try:
                m = json.loads(msg_str)
            except Exception:
                self.log.exception('client message decode exception: <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n\t%s',
                                   json.loads(msg_str))
                raise

            self.log.debug('client got message: <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n\t%s',
                           json.loads(msg_str))
            return m

        except Exception as e:
            self.log.warning('<Session %s> recv exception %s', self, e)
            raise

    async def recv_while(self, fn):
        while fn():
            m = await self.recv()
            yield m

    async def send_dict(self, do):
        json_msg = json.dumps(do)
        self.log.debug('client sent %s message: >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n\t%s',
                       do.get('action', 'action_unknown').upper(), json_msg)
        await self.conn.send(json_msg)

    def gen_message_id(self):
        self._id += 1
        _id = self._id
        return _id

    async def connect(self, uri):
        self.conn = await websockets.connect(
            uri,
            user_agent_header="internal",
        )

    async def close(self):
        await self.conn.close()
