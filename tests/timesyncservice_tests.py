import unittest
import mock
import binascii
import time

from tests.utilities import module_function_name

import timesync
from timesync.timesyncservice import TimeSyncMasterData
from timesync.timesyncservice import TimeSyncSlaveData
from timesync.timesyncservice import FilterValues 

class TestTimeSyncMasterData(unittest.TestCase):
    
    #@mock.patch(module_function_name(print))
    #def test_should_print_hello_world(self, mock_print):
    #    skeleton = python_skeleton.PythonSkeleton()
    #    skeleton.hello()
    #    mock_print.assert_called_once_with('Hello world!')


    def test_as_binary(self):    
        t_filter = FilterValues()
        t_master = TimeSyncMasterData(t_filter, tMasterForFeedback=1.2654,TOffset = 0.123)
    
        
        bytes_data = t_master.as_binary()
        hex_data = binascii.hexlify(bytes_data)
        
        expected_result = "3FF43F141205BC023FBF7CED916872B0".lower()
        
        hex_str = "".join( chr(x) for x in hex_data)
        self.assertEqual(expected_result,hex_str)
        
        
    
    def test_as_hex(self):
        pass
    
    
class TestFilterValues(unittest.TestCase):
    
    
    def fake_elapsed_time_0to5(self):
        return 3
    
    def fake_elapsed_time_5to15(self):
        return 11
    
    def fake_elapsed_time_15to30(self):
        return 17
    
    def fake_elapsed_time_30(self):
        return 31
        
    ###
    # Tests to ensure that we can get the right values according to the time that has passed. 
    
    @mock.patch.object(timesync.timesyncservice.FilterValues, "elapsed_time", fake_elapsed_time_0to5)
    def test_filter_value_between_0to5(self):
        
        fv = FilterValues()
        filter_value = fv.filter_value()
        self.assertEqual(filter_value, 0.1)
        
        
    @mock.patch.object(timesync.timesyncservice.FilterValues, "elapsed_time", fake_elapsed_time_5to15)
    def test_filter_value_between_5to15(self):
        
        fv = FilterValues()
        self.assertEqual(fv.filter_value(), 1)
        

    @mock.patch.object(timesync.timesyncservice.FilterValues, "elapsed_time", fake_elapsed_time_15to30)
    def test_filter_value_between_15to30(self):

        fv = FilterValues()
        filter_value = fv.filter_value()
        self.assertEqual(filter_value, 10)
        
        
        
    @mock.patch.object(timesync.timesyncservice.FilterValues, "elapsed_time", fake_elapsed_time_30)
    def test_filter_value_between_30(self):

        fv = FilterValues()
        filter_value = fv.filter_value()
        self.assertEqual(filter_value, 30)
        
        
     
    def test_filter_value_by_sleeping_different_amount_of_seconds(self):
        
        fv = FilterValues()
        time.sleep(6)
        
        self.assertEqual(fv.filter_value(), 1)
    
        
        
class TimeSyncSlaveDataTests(unittest.TestCase):
    
    def test_to_binary(self): 
        
        x = TimeSyncSlaveData(tSlaveMessageRecieved=1.2654,
                 tSlaveMessageSent=0.123,
                 tMasterFeedback=9.453)
        
        print(x.as_binary())
        
        
    def test_to_hex(self):
        
        x = TimeSyncSlaveData(tSlaveMessageRecieved=1.2654,
                 tSlaveMessageSent=0.123,
                 tMasterFeedback=9.453)
        
        print(x.to_hex())
        
    def test_from_binary(self):
        
        x = TimeSyncSlaveData(tSlaveMessageRecieved=1.23456,
                 tSlaveMessageSent=0.987,
                 tMasterFeedback=9.456)
        
        bytes_data = x.as_binary()
        
        y = TimeSyncSlaveData()
        y.from_binary(bytes_data)
        
        print(y.tSlaveMessageRecieved)
        print(y.tSlaveMessageSent)
        print(y.tMasterFeedback)
        
        
        
        