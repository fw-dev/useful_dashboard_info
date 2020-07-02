import asyncio
import atexit
import json
import zmq
import zmq.asyncio

from extra_metrics.logs import logger


def get_zmq_broker_xsub_endpoint(cfg):
    return f'tcp://{cfg.get_fw_api_server()}:20005'


class ZMQConnector:
    @classmethod
    def connect_to_broker(cls):
        cls.__instance = cls()
        atexit.register(cls.disconnect_from_broker)

    @classmethod
    def disconnect_from_broker(cls):
        cls.__instance.disconnect()

    def __init__(self, cfg, callback):
        self.__ctx: zmq.asyncio.Context = None
        self.__socket: zmq.asyncio.Socket = None
        self.cfg = cfg
        self.callback = callback
        asyncio.create_task(self.start())

    async def start(self):
        self.__ctx = zmq.asyncio.Context()
        self.__socket = self.__ctx.socket(zmq.SUB)

        # in compat mode; there is NO subscribe keypair data
        key_pair = self.cfg.get_zmq_subscribe_keypair()
        if key_pair is not None:
            self.__socket.curve_serverkey = key_pair.strip()  # the first line is the public key

            # for the client socket, the curve key pair will be regenerated all the time
            # the important part for "authentication" is the server "public" key
            self.__socket.curve_publickey, self.__socket.curve_secretkey = zmq.curve_keypair()
        else:
            logger.info("no ZMQ subscriber keypair exists; assuming compat mode")

        self.__socket.connect(get_zmq_broker_xsub_endpoint(self.cfg))

        # Subscribe to all topics
        self.__socket.subscribe('')

        logger.info("filewave server event subscriber has started")

        asyncio.create_task(self.forward_events())

    async def forward_events(self):
        # forward JSON events into the callback
        while self.__socket:
            logger.debug('waiting for events from FileWave...')

            msg = await self.__socket.recv_multipart()
            topic = msg[0].decode('utf-8')
            body = json.loads(msg[3]) if msg[2] == b'json' else msg[3]

            try:
                logger.debug(f'new notification: {topic}, {body}')
                self.callback(topic, body)
            except Exception:
                # I really don't care what the consumer did with this
                pass

    def disconnect(self):
        self.__socket.close()
        self.__socket = None
