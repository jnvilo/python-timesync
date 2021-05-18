import socket
import sys
import argparse
import binascii
import struct 


from locationservice import settings
from locationservice.daemon import Daemon
import logging
log = logging.getLogger("udpserver")


class UDPServer(Daemon):
    
    def __init__(self, ip, port, pidfile, log=None):
        
        self.ip = ip
        self.port = port
    
        if log is not None: 
            self.log = log
        else:
            self.log = logging.getLogger("udpserver")
        
        super(UDPServer, self).__init__(pidfile, log=self.log)

    def run_udp_server(self, ip, port):
        """
        Listens on the provided ip and port and prints the recieved 
        messages to the console. 
        """
        try:
            # Create a UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Bind the socket to the port
            server_address = (ip, port)
        
            sock.bind(server_address)
            self.log.info("-"*80)
            self.log.info('starting up on {} port {}'.format(*server_address))
            self.log.info("-"*80)
        except OSError as e:
            self.log.fatal("Failed to start server. {}".format(e))
            
    
        while True:
            #forever cycle through recieving and sending data.
            address = self.recieve_data(sock)
            self.send_response(sock, address)
    
    def recieve_data(self, sock):
        """Implementation is done in a subclass"""
        raise NotImplementedError("Not Implemented")
    
    def send_response(self, sock, address):
        """Implementation is expected to be done in a subclass"""
        raise NotImplementedError("Not Implemented")
        
        
    def run(self):
        self.run_udp_server(self.ip, self.port)
        
        
