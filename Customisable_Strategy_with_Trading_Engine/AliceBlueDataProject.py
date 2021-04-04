# -----------------------------------------------------------
# Import required libraries
# -----------------------------------------------------------

import os
import time
import json
import math
import talib
import selenium
import datetime
import requests
import threading
import numpy as np
import pandas as pd
import telegram_bot
from alice_blue import *
from datetime import timedelta
from jugaad_trader import Zerodha
from sleep_function import sleeper
from collections import namedtuple
from collections import defaultdict


# -----------------------------------------------------------
# Class to get live data stream from Alice Blue
# -----------------------------------------------------------


class AmadeusData_AliceBlue():
    
    # Access user credentials from pre-stored CSV and save them into these variables
    username, password, twoFA, api_secret = pd.read_csv('alice_blue_credentials.csv').iloc[0]
    
    # -----------------------------------------------------------
    # Init Method accepts the timeframe to resample the tick data 
    # to and a dictionary 'instrument_exchange' which specifies the
    # instruent and exchange along with other required parameters
    # (refer main file to set input)
    # -----------------------------------------------------------
    
    def __init__(self, timeframe, instrument_exchange):
        
        # Create access_token using login_and_get_access_token() function with your username, password, 2FA and api_secret
        self.access_token = AliceBlue.login_and_get_access_token(username = self.username, 
                                                                 password = self.password, 
                                                                 twoFA = self.twoFA,  
                                                                 api_secret = self.api_secret)
        
        # Once you have your access_token, you can create an AliceBlue object with your access_token, username and password
        self.alice = AliceBlue(username = self.username, password = self.password, access_token = self.access_token)
    
        # Instruments are represented by instrument objects. These are named-tuples that are created while 
        # getting the master contracts. They are used when placing an order and searching for an instrument.
        self.Instrument = namedtuple('Instrument', ['exchange', 'token', 'symbol',
                                      'name', 'expiry', 'lot_size'])
    
        # Initialise socket to False until subscribed to instruments
        self.socket_opened = False
        
        # Set timeframe as a class attribute
        self.timeframe = timeframe

        # Create a default dictionary which stores empty dataframes for any default key, 
        # to store live tick data once an instrument is subscribed to
        self.raw_data = defaultdict(
            lambda: pd.DataFrame(columns = ['datetime', 'ticker', 'ltp', 'cum_volume', 'volume']).set_index('datetime'))

        # Create a default dictionary which stores empty dataframes for any default key, 
        # to store resampled data once an instrument is subscribed to
        self.data = defaultdict(
            lambda: pd.DataFrame(columns = ['datetime', 'ticker', 'open', 'high', 'low', 'close', 'volume', 'date', 'time']).set_index('datetime'))
        
        # Set instrument_exchange dictionary input as a class attribute
        self.instrument_exchange = instrument_exchange
        
    
    # -----------------------------------------------------------
    # Get Live Quote Update
    # -----------------------------------------------------------
    
    def get_ltp(self, message):
    
        # Set message output as class attribute - this would be updated once websocket is started
        self.message = message
        
        # Extract instrument name from message and set it as class attribute
        self.instrument = self.message['instrument'].symbol

        # Extract timestamp from message and set it as class attribute
        self.timestamp = datetime.datetime.fromtimestamp(self.message['exchange_time_stamp'])
        
        # Live update ticker and volume extracted from message and append it as row to the raw_data
        self.raw_data[self.instrument] = self.raw_data[self.instrument].append(
                            pd.Series({'ticker' : self.instrument, 'ltp' : self.message['ltp'], 'cum_volume' : self.message['volume']}, 
                            name = self.timestamp))
        
        # Extract volume from cumulative volume by taking difference
        self.raw_data[self.instrument]['volume'] = self.raw_data[self.instrument]['cum_volume'].diff()
        
    
    # -----------------------------------------------------------
    # Open Socket Callback
    # -----------------------------------------------------------
     
    def open_callback(self):
    
        # Set socket_opened to True
        self.socket_opened = True
        
    
    # -----------------------------------------------------------
    # Start Live Data Feed and Start Websocket
    # -----------------------------------------------------------
    
    def start_live_feed(self):
    
        # Start Alice Blue Websocket and set subscribe callback to get_ltp class method and 
        # socket open callback to open_callback class method
        self.alice.start_websocket(subscribe_callback=self.get_ltp,
                          socket_open_callback=self.open_callback,
                          run_in_background=True)

        # Wait and do nothing until socket_opened turns True
        while(self.socket_opened==False):
            pass

        # Create a Zerodha object to get historical data using Jugaad Trader
        kite = Zerodha()
        # Automatically load pre-stored credentials
        kite.load_creds()
        # Login to Zerodha with loaded credentials
        kite.login()
        
        # Iterate over the keys in instrument_exchange dictionary, which are the instrument names
        for key in self.instrument_exchange:
        
            # Subscribe the particular instrument to alice blue by passing the instrument symbol name and exchange name
            self.alice.subscribe(self.alice.get_instrument_by_symbol(self.instrument_exchange[key]['exchange'], key), LiveFeedType.COMPACT)

            # Check if the particular instrument is Futures
            if (key[-3:] == 'FUT'):

                # Store the particular instrument in the form Zerodha can extract its token number
                ins_kite = self.instrument_exchange[key]['exchange'] + ':' + key.split(' ')[0] + str(datetime.date.today().year)[2:] + key.split(' ')[1] + key.split(' ')[2]
                
                # Extract the instrument's token number using quote method from Zerodha object
                ins_kite_number = kite.quote(ins_kite)[ins_kite]['instrument_token']
            
            # If the instrument is not Futures
            else:

                # Store the particular instrument in the form Zerodha can extract its token number
                ins_kite = self.instrument_exchange[key]['exchange'] + ':' + key
                
                # Extract the instrument's token number using quote method from Zerodha object
                ins_kite_number = kite.quote(ins_kite)[ins_kite]['instrument_token']
                
            # Define date from when you want historical data
            # in this case, it is from 5 days ago
            from_date = datetime.date.today() - datetime.timedelta(days = 5)

            # Define date till when you want historical data
            # in this case, it is until the current time
            to_date = datetime.date.today()

            # Define timeframe for the historical data's frequency
            interval = "minute"

            # Save historical data to class attribute data and append live resampled data to this eventually
            self.data[key] = pd.DataFrame(kite.historical_data(ins_kite_number, from_date, to_date, interval, continuous=False, oi=False))
   
            ### Clean the Zerodha historical data to match its format to AliceBlue live data ###
    
            # Create datetime column which is equal to the Zerodha historical data's date column
            self.data[key]['datetime'] = self.data[key]['date']
            
            # Create new column ticker to store symbol name
            self.data[key]['ticker'] = key

            # Reassign date column to the date extracted from datetime column
            self.data[key]['date'] = self.data[key]['datetime'].apply(lambda x : x.date())
            
            # Create time column to the time extracted from datetime column
            self.data[key]['time'] = self.data[key]['datetime'].apply(lambda x : x.time())

            # Reorder column names in the dataframe
            self.data[key] = self.data[key][['datetime','ticker','open','high','low','close','volume','date','time']]
            
            # Reassign datetime column as a combined string form of date and time from the respective columns
            self.data[key]['datetime'] = self.data[key]['date'].apply(str) + self.data[key]['time'].apply(str)
            
            # Set datetime column to datetime format using strptime method
            self.data[key]['datetime'] = self.data[key]['datetime'].apply(lambda x : datetime.datetime.strptime(x, '%Y-%m-%d%H:%M:%S'))
            
            # Set datetime column as index
            self.data[key].set_index('datetime', inplace=True)
            
            
    # -----------------------------------------------------------
    # Static method to obtain required time delta from timeframe
    # This will be required by the data resampling function
    # Refer class method resample_data to understand requirement
    # -----------------------------------------------------------
    
    @staticmethod
    def obtain_timedelta(timeframe):

        # If the timeframe is in seconds, as indicated by the last element of the string being S
        if timeframe[-1] == 'S':
            
            # Set timedelta to seconds equal to the number specified before the last element
            td = datetime.timedelta(seconds = int(timeframe[:-1]))

        # Else If the timeframe is in minutes, as indicated by the last element of the string being T
        elif timeframe[-1] == 'T':
            
            # Set timedelta to minutes equal to the number specified before the last element
            td = datetime.timedelta(minutes = int(timeframe[:-1]))

        # Else If the timeframe is in minutes, as indicated by the last 3 elements of the string being min
        elif timeframe[-3:].lower() == 'min':
            
            # Set timedelta to minutes equal to the number specified before the last 3 elements
            td = datetime.timedelta(minutes = int(timeframe[:-3]))

        # Else If the timeframe is in hours, as indicated by the last element of the string being H
        elif timeframe[-1] == 'H':
            
            # Set timedelta to hours equal to the number specified before the last element
            td = datetime.timedelta(hours = int(timeframe[:-1]))

        # Else If the timeframe is in days, as indicated by the last element of the string being D
        elif timeframe[-1] == 'D':
            
            # Set timedelta to days equal to the number specified before the last element
            td = datetime.timedelta(days = int(timeframe[:-1]))

        # Else If the timeframe is in weeks, as indicated by the last element of the string being W
        elif timeframe[-1] == 'W':
            
            # Set timedelta to weeks equal to the number specified before the last element
            td = datetime.timedelta(weeks = int(timeframe[:-1]))

        # If none of the above conditions are met
        else:
            
            # Set timedelta to None
            td = None

        # Return the calculated timedelta
        return td
    
    
    # -----------------------------------------------------------
    # Resample Data to required timeframe
    # -----------------------------------------------------------
    
    def resample_data(self):
    
        # Set the flag to check thread run to True
        self.thread_resample_run = True
        
        # Run while the flag to check thread run is True
        while self.thread_resample_run:

            # Iterate over instrument symbol names
            for ins in self.instrument_exchange:
                
                # If the data feed hasn't begun, that is the length of raw_data is 0 
                if len(self.raw_data[ins]) == 0:

                    # Then continue
                    continue
                  
                # Create a temporary dataframe which is resampled from raw_data at the mentioned timeframe
                temp = pd.DataFrame({'open' : self.raw_data[ins]['ltp'].resample(self.timeframe).first(),
                                     'high' : self.raw_data[ins]['ltp'].resample(self.timeframe).max(),
                                     'low' : self.raw_data[ins]['ltp'].resample(self.timeframe).min(),
                                     'close' : self.raw_data[ins]['ltp'].resample(self.timeframe).last(),
                                     'volume' : self.raw_data[ins]['volume'].resample(self.timeframe).sum()
                                    })

                # Add a new column to the temporary dataframe to save the instrument ticker name
                temp['ticker'] = ins
                
                # Add a new column to the temporary dataframe to save the resampled date
                temp['date'] = temp.index.date
                
                # Add a new column to the temporary dataframe to save the resampled time
                temp['time'] = temp.index.time

                # Add the first row of the temp dataframe at that particular index in class attribute data
                self.data[ins].at[temp.index[0]] = temp.iloc[0]
                
                # If the datetime index of the last row of temporary dataframe is greater than 
                # the last row of class attribute data
                if temp.index[-1] > self.data[ins].index[-1]:

                    # Use the static method obtain_timedelta to find out what the next datetime index
                    # in class attribute data should be
                    next_tick = self.data[ins].index[-1] + self.obtain_timedelta(self.timeframe)

                    # Discard all data before the next_tick datetime index from raw_data in order to resample it again in 
                    # the next loop and extract latest resampled data from the first row of the temporary data formed 
                    # by resampling raw_data
                    self.raw_data[ins] = self.raw_data[ins][self.raw_data[ins].index > next_tick]
    
    
    # -----------------------------------------------------------
    # Start threading to run resampling in the background
    # -----------------------------------------------------------
    
    def start_thread(self):

        # Create new thread for resample_data method
        self.thread_resample = threading.Thread(target = self.resample_data)
        
        # Start running the thread
        self.thread_resample.start()
        
    # -----------------------------------------------------------
    # Start Live Data Streaming by subscribing to specified 
    # instruments and start the resampling thread in the background
    # Run this only once
    # -----------------------------------------------------------
    
    def get_live_data_initialise(self):
        
        # Subscribe to instruments and get their historical data
        # We have to make sure to run this only once and not anymore
        self.start_live_feed()
        self.start_thread()
       
    # -----------------------------------------------------------
    # Terminate the resampling thread in the background
    # -----------------------------------------------------------
    
    def terminate_thread(self):
            
        self.thread_resample_run = False
        self.thread_resample.join()