import asyncio
import socket
import signal
import functools
import logging

from masterserver import MasterServer


class Transport():
    def __init__(self, storage, protocols):
        logging.debug(f"{self.__class__.__name__ } - Initialising transport")
        self.loop = asyncio.get_event_loop()
        self.signal()
        self.storage = storage
        self.protocols = protocols

        self.listener(
                socket.AF_INET,
                ('0.0.0.0', 27900)
        )

        self.v6_udp_transport = None
        self.health_check()

    def signal(self):
        logging.debug(f"{self.__class__.__name__ } - Setting up signals")
        signals = ('SIGINT', 'SIGTERM')
        for signame in signals:
            self.loop.add_signal_handler(
                getattr(signal, signame),
                functools.partial(self.shutdown, signame)
            )

    async def listener(self,
                 socket_family,
                 bind):

        logging.debug(f"{self.__class__.__name__ } - Setting up master listener on {bind[0]}:{bind[1]}")

        self.v4_udp_transport, self.v4_udp_protocol = await self.loop.create_datagram_endpoint(
            lambda: MasterServer(self.storage, self.protocols),
            family=socket_family,
            local_addr=bind
        )

    async def health_check(self,
                     socket_family=socket.AF_INET,
                     host='0.0.0.0',
                     port=8080):

        logging.debug(f"{self.__class__.__name__ } - Setting up health check listener on {host}:{port}")

        self.healt_check_transport, self.healt_check_protocol = await self.loop.create_server(
            lambda: HealthCheck(),
            family=socket_family,
            host=host,
            port=port)

    async def shutdown(self, sig):
        logging.debug(f"{self.__class__.__name__ } - Caught {sig}")
        if self.healt_check_transport:
            logging.debug(f"{self.__class__.__name__ } - Closing health check listener")
            await self.healt_check_transport.close()

        if self.v4_udp_transport:
            logging.debug(f"{self.__class__.__name__ } - Closing IPv4 UDP transport")
            await self.v4_udp_transport.close()

        if self.v6_udp_transport:
            logging.debug(f"{self.__class__.__name__ } - Closing IPv6 UDP transport")
            await self.v6_udp_transport.close()

        self.loop.stop()


class HealthCheck(asyncio.Protocol):
    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        # logging.debug(f"{self.__class__.__name__ } - Received health check ping")
        self.transport.write(b'HTTP/1.1 200 Success\n')
