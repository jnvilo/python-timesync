import struct
from datetime import datetime
import binascii
import argparse
import logging
import redis
import logging.config

from redis.exceptions import (
    RedisError,
    ConnectionError,
    TimeoutError,
    BusyLoadingError,
    ResponseError,
    InvalidResponse,
    AuthenticationError,
    NoScriptError,
    ExecAbortError,
    ReadOnlyError
)

from timesync.udpserver import UDPServer
logger = logging.getLogger("timesync")

DEFAULT_PORT = 8089
LISTEN_ADDRESS="0.0.0.0"
REDIS_PASSWORD="xImpZL0MvunJrjZhImBnJCubs7rcvggnrFWGfIu3aINE9LW35rqPBrwGEgAgBL0mXR/yt4cBuDhtJMuE"
LOC_TIMESYNC_PORT = 8090

class FilterValues(object):

    """
    A class to keep track of Filter values. This returns the filter value
    according to how much time has elapsed and the values are
    defined as :

    SEC                         --             Value
    0 to 5                                     0.1
    5 to 15                  --                1
    15 to 30                --                 10
    30 and above     --                        30
    """

    def __init__(self, *args, **kwargs):

        #Initialize our start time. This is modifed by reset() back to 0.
        self._starttime = datetime.now()



    def elapsed_time(self):
        #returns the elapsed time in seconds
        self._elapsed_time = (datetime.now() - self._starttime).total_seconds()

        return self._elapsed_time

    def reset(self):
        "A method to reset the state of the filter"
        self._starttime = datetime.now()
        self._elapsed_time = 0

        logger.debug("Reseting t_filter to time 0.")

    def filter_value(self):
        """
        Returns the filter value according to how much time has elapsed.
        """

        if  0< self.elapsed_time()<5:
            return 0.1
        elif 5<self.elapsed_time()<15:
            return 1
        elif 15<self.elapsed_time()<30:
            return 10
        elif self.elapsed_time()>=30:
            return 30
        else:
            #A catchall
            return 0.1

class TimeSyncMasterData(object):
    """
    A class to encapsulate the data that we send to the Slave. We only have
    two values but we use a class to add methods to turn it to binary
    or hex data.
    """

    def __init__(self, tfilter, tMasterForFeedback=0, TOffset=0):

        self.logger = logging.getLogger(self.__class__.__name__)

        self.tMasterForFeedBack = tMasterForFeedback
        self.TOffset = TOffset

        #This is used to keep the value since the last calculations was done.
        self.t_offset_last_value = 0

        #This is used to calculate delta_T
        self.ZeroTime = datetime.now()
        self.last_calculation_time = datetime.now()

        #Create an instance where to get Filter Values.
        self.time_filter = FilterValues()
        self.t_offset_last_value = 0

    def __str__(self):

        msg = "TimeSyncMasterData(tMasterForFeeback={}, TOffset={}"
        return msg.format(self.tMasterForFeedBack, self.TOffset)


    def do_calculation(self, sync_slave_data):
        """
        We expect to recieve a class called TimeSyncSlaveData which contains the
        following values:

            tSlaveMessageRecieved
            tSlaveMessageSent
            tMasterFeedback
        """
        #check if we need to reset our filter.
        elapsed_time_since_last_message_recieved = (datetime.now() - self.last_calculation_time).total_seconds()
        self.logger.debug("last message recieved was: {} seconds ago".format(elapsed_time_since_last_message_recieved))

        if elapsed_time_since_last_message_recieved > 30:
            self.time_filter.reset()
        

        #we get the data sent by the slave.
        tSlaveMessageRecieved = sync_slave_data.tSlaveMessageRecieved
        tSlaveMessageSent = sync_slave_data.tSlaveMessageSent
        tMasterFeedback = sync_slave_data.tMasterFeedback

        #Check if we need to reset the t_filter

        self.logger.debug("=======TimeSyncMasterData Calculations========================")
        msg = "Received from Slave: tSlaveMessageRecieved={}, tSlaveMessageSent={}, tMasterFeedback={}"

        self.logger.debug(msg.format(tSlaveMessageRecieved, tSlaveMessageSent, tMasterFeedback))

        #we need tMasterCurrent - Graham says this is just the elapsed time since start.
        time_now = datetime.now()
        #tMasterCurrent = (time_now - self.ZeroTime).total_seconds()
        tMasterCurrent = time_now.timestamp()

        msg= "Computed:  tMasterCurrent: subtracting time now({}) to self.ZeroTime({}) = {}"
        self.logger.debug(msg.format(time_now, self.ZeroTime, tMasterCurrent))


        #tMasterCurrent
        #Now we calculate t_delay according to the formula:

        t_delay = (tSlaveMessageRecieved - tMasterFeedback + tMasterCurrent - tSlaveMessageSent)/2

        msg = """Computed:  "t_delay = (tSlaveMessageRecieved - tMasterFeedback + tMasterCurrent - tSlaveMessageSent)/2"  =  {}"""
        self.logger.debug(msg.format(t_delay))

        t_offset_raw = (tSlaveMessageRecieved - tMasterFeedback - tMasterCurrent + tSlaveMessageSent)/2
        msg = """Computed: "t_offset_raw = (tSlaveMessageRecieved - tMasterFeedback - tMasterCurrent + tSlaveMessageSent)/2"  = {}"""
        self.logger.debug(msg.format(t_offset_raw))

        # ##
        #Now we calculate the TOffset
        #

        #Step 1: calculate the delta_T (documentation/Graham says this is the time elapsed since
        #the last time we did a calculation)
        delta_T = (datetime.now() - self.last_calculation_time).total_seconds()

        msg = "self.last_calculation_time = {}".format(self.last_calculation_time)
        self.logger.debug(msg)

        msg = """Computed: "delta_T = (datetime.now() - self.last_calculation_time).total_seconds()" = {} """
        self.logger.debug(msg.format(delta_T))



        #Step 2: Get the filter value. This is made easy since implementation is all on TimeFilter
        # See TimeFilter class further above.
        t_filter = self.time_filter.filter_value()
        msg = "Using t_filter = {}".format(t_filter)
        self.logger.debug(msg)

        #Step3 Finaly we can calculate the value.
        Toffset =(1/(1 + (t_filter/delta_T)))*(t_offset_raw - self.t_offset_last_value) + self.t_offset_last_value

        msg = """Computed: "Toffset =(1/(1 + (t_filter/delta_T)))*(t_offset_raw - self.t_offset_last_value) + self.t_offset_last_value"  = {}"""
        self.logger.debug(msg.format(Toffset))
        #We are done but update t_offset_last_value to the newest value for
        # next time calculations.

        self.t_offset_last_value = Toffset
        msg = "Setting self.t_offset_last_value = Toffset.  (self.t_offset_last_value is now = {}"
        self.logger.debug(msg.format(Toffset))


        #Also update self.last_calculation_time to now so that we remember when was the last time we did a calculation
        self.last_calculation_time = datetime.now()
        msg =  "Setting self.last_calculation_time = datetime.now(). it is now set to {}. We need this for next iteration calculations. "
        self.logger.debug(msg.format(self.last_calculation_time))




        #Now all we need is to set the values and we are done.
        self.logger.debug("=======Exiting TimeSyncMasterData.do_calculation()========================")


        self.tMasterForFeedBack = tMasterCurrent
        self.TOffset = Toffset


        
        

    def as_binary(self):
        """
        A method to convert the tMasterForFeeback and TOffset to package it off
        as a binary data ready for sending to the Slave.

        This method packs the data as bytes. struct.pack requires the format as
        the first parameter and the formatting is as follows. Note: We have doubles
        so we use !d.


        Character       Byte order       Size        Alignment
        @               native           native      native
        =               native           standard     native
        <               little-endian    standard    none
        >               big-endian       standard    none
        !               network (= big-endian) standard none

        """

        data = bytes()

        data = data + struct.pack("!d", self.tMasterForFeedBack)
        data = data + struct.pack("!d", self.TOffset)

        return data


    def as_hex(self):
        """
        Returns a hex representation of the data.

        If we create an instance of the class with the following values,

        tsmd = TimeSyncMasterData(tMasterForFeedback=1.2654,
                                  TOffset = 0.123)

        then:

        calling as_hex() should give us back the hex data value of:

        "3FF43F141205BC023FBF7CED916872B0"
        """

        #conversion of binary to hex bytes array is simple with python binascii.
        hex_data = binascii.hexlify(self.as_binary())

        #The hex_data is still a byte array. We need to convert it to a
        #proper python string
        return "".join( chr(x) for x in hex_data)


class TimeSyncSlaveData(object):
    """
    A class to encapsulate the data we recieve from the Slave.
    This is then passed to TimeSyncMasterData.

    We use a class to encapsulate the data we recieve from the slave because
    it makes it easier to do operations on the data from an object oriented
    point of view. This class implements conversions of the data from or to hex or
    binary or print the data for logging or display purposes.
    """

    def __init__(self,  tSlaveMessageRecieved=0, tSlaveMessageSent=0, tMasterFeedback=0):

        self.tSlaveMessageRecieved = tSlaveMessageRecieved
        self.tSlaveMessageSent = tSlaveMessageSent
        self.tMasterFeedback = tMasterFeedback


    def to_hex(self):
        """
        Returns a hex represtantion of the slave data
        """
        hex_data = binascii.hexlify(self.as_binary())

        #The hex_data is still a byte array. We need to convert it to a
        #proper python string
        return "".join( chr(x) for x in hex_data)



    def as_binary(self):
        """
        Converts the following data into a bytearray.

        self.tSlaveMessageRecieved = tSlaveMessageRecieved
        self.tSlaveMessageSent = tSlaveMessageSent
        self.tMasterFeedback = tMasterFeedback

        The binary data is packed as doubles.

        Test Values provided are as document in AFW_Kommunikation_ABX_Cloud_v1.4.xlsx

        double_tSlaveMessageReceived = double(1.2654);
        double_tSlaveMessageSent = double(0.123);
        double_tMasterFeedback = double(9.453);

        and hex data as: "3FF43F141205BC023FBF7CED916872B04022E7EF9DB22D0E"
        """

        data = bytes()

        data = data + struct.pack("!d", self.tSlaveMessageRecieved)
        data = data + struct.pack("!d", self.tSlaveMessageSent)
        data = data + struct.pack("!d", self.tMasterFeedback)

        return data

    def from_binary(self,data):
        """
        This fills up the following internal class variables from the binary data
        that is passed as argument.
        """

        #Get 8 bytes:

        bytes_SlaveMessageRecieved = data[0:8]
        bytes_SlaveMessageSent = data[8:16]
        bytes_tMasterFeedback = data[16:24]

        self.tSlaveMessageRecieved = struct.unpack('!d', bytes_SlaveMessageRecieved)[0]
        self.tSlaveMessageSent = struct.unpack('!d', bytes_SlaveMessageSent)[0]
        self.tMasterFeedback = struct.unpack('!d', bytes_tMasterFeedback)[0]


    def __str__(self):

        msg = "TimeSyncSlaveData(tSlaveMessageRecieved={}, tSlaveMessageSent={}, tMasterFeedback={})"
        return msg.format(self.tSlaveMessageRecieved, self.tSlaveMessageSent, self.tMasterFeedback)


        
class TimeSyncService(UDPServer):
    """
    Implements the recieve_data and send_response methods of a UDPServer.

    UDPServer implements the blocking loop as follows:

          while True:
            #forever cycle through recieving and sending data.
            address = self.recieve_data(sock)
            self.send_response(sock, address)

    So we need to implement both methods in our subclass.
    """

    def __init__(self, ip, port, pidfile):
        #pass the init param to the UDPServer parent class
        super(TimeSyncService, self).__init__(ip, port, pidfile)

        self.redis_con = redis.Redis(host='localhost', port=6379, db=0, password=REDIS_PASSWORD)
        
        #client_data dict is a dict where we use the source IP of the client as
        #the key and reference a ClientData dataclas
        self.client_data_dict = {}
        
    def recieve_data(self, sock):
        """
        Here we implement the recieve data of UDPServer. Everytime the udpserver
        recieves data, it calls this function and then immediately calls
        the send_response function after this exits.
        """

        self.data, address = sock.recvfrom(71)
        return address


    def send_response(self, sock, address):
        """
        Deal with the data received from the slave and send back
        a response.
        """
        
        ipv4_address, port = address
        
        timeSyncMasterData = self.client_data_dict.get(ipv4_address, None)
        
        if timeSyncMasterData is None:
            msg = "First time seeing {}. Instantiating a TimeSyncMasterData for this client."
            logger.info(msg.format(ipv4_address))
            t_filter = FilterValues()
            timeSyncMasterData =  TimeSyncMasterData(FilterValues())
            last_message_recieved = datetime.now()

            self.client_data_dict.update({ipv4_address: timeSyncMasterData})
        else:
            msg = "Loaded previous data session for client: {}".format(ipv4_address)
            logger.info(msg)
        #Get the timeSyncMasterData
        #timeSyncMasterData = timeSyncMasterData

        timeSyncSlaveData = TimeSyncSlaveData()
        timeSyncSlaveData.from_binary(self.data)
        logger.info("Recieved data: {} from {}".format(timeSyncSlaveData,ipv4_address))

        timeSyncMasterData.do_calculation(timeSyncSlaveData)
        logger.info("Calc Results: {}".format(timeSyncMasterData))

        response_data = timeSyncMasterData.as_binary()
        sent = sock.sendto(response_data, address)

       
       
        try:
            self.redis_con.set("tMasterForFeedback", timeSyncMasterData.tMasterForFeedBack)
            #Also save tMasterForFeedback to Redis
            msg = "Wrote tMasterForFeedback = {} to redis".format(timeSyncMasterData.tMasterForFeedBack)
            logger.debug(msg)        
        except ConnectionError as e:
            msg = "Failed to connect to Redis backend. tMasterForFeedback will not be sent to redis."
            logger.fatal(msg)
            
def main2():

    #Parse the arguments
    parser = argparse.ArgumentParser()

    parser.add_argument("--ip", help="The IP to listen to. Defaults to all interfaces.",
                        default=LISTEN_ADDRESS)
    parser.add_argument("--port",help="The udp server port. Defaults to 1773",
                        default=LOC_TIMESYNC_PORT)

    #parser.add_argument("--loglevel", help= """Set Loglevel to ["DEBUG", "INFO","WARN", "FATAL"] """)

    logchoice_parser = parser.add_subparsers()
    parser_list = logchoice_parser.add_parser('setloglevel')
    loglevel_help = """set Logging to one of: ["DEBUG", "INFO","WARN", "FATAL"]. Default is DEBUG """
    parser_list.add_argument('list_level', default='DEBUG', nargs='?', choices=["DEBUG", "INFO","WARN", "FATAL"], help=loglevel_help)

    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--start', action='store_true', help='Starts %(prog)s daemon')
    action.add_argument('--stop', action='store_true', help='Stops %(prog)s daemon')
    action.add_argument('--restart', action='store_true', help='Restarts %(prog)s daemon')
    action.add_argument('--nodaemon', action='store_true', help='Runs carservice in the foreground and will exit when terminal is closed or ctr-C is pressed.')
    args = parser.parse_args()

    #Args is a namespace that contains the following:
    #Namespace(ip='0.0.0.0', port=8087, restart=False, start=True, stop=False, **{'loglevel=': 'DEBUG'})


    LOGGING = {
            'version': 1,
            'formatters': {
                'default': {'format': '%(asctime)s - %(levelname)s - %(message)s', 'datefmt': '%Y-%m-%d %H:%M:%S'}
            },
            'handlers': {
                'console': {
                    'level': 'DEBUG',
                    'class': 'logging.StreamHandler',
                    'formatter': 'default',
                    'stream': 'ext://sys.stdout'
                },
                'file': {
                    'level': 'DEBUG',
                    'class': 'logging.handlers.RotatingFileHandler',
                    'formatter': 'default',
                    'filename': "/opt/software/logs/loc_timesync-{}.log".format(datetime.now().strftime('%Y_%m_%d')),
                    'maxBytes': 102400, #rotate logs at 100MBytes
                    'backupCount': 3
                }
            },
            'loggers': {
                'default': {
                    'level': 'DEBUG',
                    'handlers': ['console', 'file']
                },
                'timesync': {
                    'level': 'DEBUG',
                    'handlers': ['console', 'file']
                } ,
                'TimeSyncMasterData':{
                    'level': 'DEBUG',
                    'handlers': ['console', 'file']
                } ,
            },

            'disable_existing_loggers': False
        }

    logging.config.dictConfig(LOGGING)




    logger.debug("Called with args: {}".format(args))
    port = args.port
    ip = args.ip



    server = TimeSyncService(ip, LOC_TIMESYNC_PORT, '/tmp/loc_timesyncservice.pid')

    if args.start:
        server.start()

    elif args.stop:
        server.stop()
    elif args.restart:
        server.restart()
    elif args.nodaemon:
        server.run()



def main():

    #Parse the arguments
    parser = argparse.ArgumentParser()

    parser.add_argument("--ip", help="The IP to listen to. Defaults to all interfaces.",
                        default=LISTEN_ADDRESS)
    parser.add_argument("--port",help="The udp server port. Defaults to 1773",
                        default=DEFAULT_PORT)

    #parser.add_argument("--loglevel", help= """Set Loglevel to ["DEBUG", "INFO","WARN", "FATAL"] """)

    logchoice_parser = parser.add_subparsers()
    parser_list = logchoice_parser.add_parser('setloglevel')
    loglevel_help = """set Logging to one of: ["DEBUG", "INFO","WARN", "FATAL"]. Default is DEBUG """
    parser_list.add_argument('list_level', default='DEBUG', nargs='?', choices=["DEBUG", "INFO","WARN", "FATAL"], help=loglevel_help)

    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--start', action='store_true', help='Starts %(prog)s daemon')
    action.add_argument('--stop', action='store_true', help='Stops %(prog)s daemon')
    action.add_argument('--restart', action='store_true', help='Restarts %(prog)s daemon')
    action.add_argument('--nodaemon', action='store_true', help='Runs carservice in the foreground and will exit when terminal is closed or ctr-C is pressed.')
    args = parser.parse_args()

    #Args is a namespace that contains the following:
    #Namespace(ip='0.0.0.0', port=8087, restart=False, start=True, stop=False, **{'loglevel=': 'DEBUG'})


    LOGGING = {
            'version': 1,
            'formatters': {
                'default': {'format': '%(asctime)s - %(levelname)s - %(message)s', 'datefmt': '%Y-%m-%d %H:%M:%S'}
            },
            'handlers': {
                'console': {
                    'level': 'DEBUG',
                    'class': 'logging.StreamHandler',
                    'formatter': 'default',
                    'stream': 'ext://sys.stdout'
                },
                'file': {
                    'level': 'DEBUG',
                    'class': 'logging.handlers.RotatingFileHandler',
                    'formatter': 'default',
                    'filename': "/opt/software/logs/timesync-{}.log".format(datetime.now().strftime('%Y_%m_%d')),
                    'maxBytes': 102400, #rotate logs at 100MBytes
                    'backupCount': 3
                }
            },
            'loggers': {
                'default': {
                    'level': 'DEBUG',
                    'handlers': ['console', 'file']
                },
                'timesync': {
                    'level': 'DEBUG',
                    'handlers': ['console', 'file']
                } ,
                'TimeSyncMasterData':{
                    'level': 'DEBUG',
                    'handlers': ['console', 'file']
                } ,
            },

            'disable_existing_loggers': False
        }

    logging.config.dictConfig(LOGGING)




    logger.debug("Called with args: {}".format(args))
    port = args.port
    ip = args.ip



    server = TimeSyncService(ip, port, '/tmp/timesyncservice.pid')

    if args.start:
        server.start()

    elif args.stop:
        server.stop()
    elif args.restart:
        server.restart()
    elif args.nodaemon:
        server.run()



if __name__ == "__main__":
    main()

