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
from sleep_function import sleeper
from collections import namedtuple
from collections import defaultdict
from jugaad_trader import Zerodha

class AmadeusData_AliceBlue():
    
    username, password, twoFA, api_secret = pd.read_csv('alice_blue_credentials.csv').iloc[0]
    
    def __init__(self, timeframe, ins_exc):
        
        self.access_token = AliceBlue.login_and_get_access_token(username = self.username, 
                                                                 password = self.password, 
                                                                 twoFA = self.twoFA,  
                                                                 api_secret = self.api_secret)
        
        self.alice = AliceBlue(username = self.username, password = self.password, access_token = self.access_token)
    
        self.Instrument = namedtuple('Instrument', ['exchange', 'token', 'symbol',
                                      'name', 'expiry', 'lot_size'])
    
        self.socket_opened = False
        
        self.timeframe = timeframe

        self.raw_data = defaultdict(
            lambda: pd.DataFrame(columns = ['datetime', 'ticker', 'ltp', 'cum_volume', 'volume']).set_index('datetime'))

        self.data = defaultdict(
            lambda: pd.DataFrame(columns = ['datetime', 'ticker', 'open', 'high', 'low', 'close', 'volume', 'date', 'time']).set_index('datetime'))
        
        self.ins_exc = ins_exc
        
        self.instruments = list(self.ins_exc.keys())
        
    def get_live_data(self):
        
        self.start_live_feed()
        self.start_thread()
        
    def get_ltp(self, message):
    
        self.message = message
        
        self.instrument = self.message['instrument'].symbol
        
        if self.instrument not in self.instruments:
            self.instruments.append(self.instrument)

        self.timestamp = datetime.datetime.fromtimestamp(self.message['exchange_time_stamp'])
        
        self.raw_data[self.instrument] = self.raw_data[self.instrument].append(
                            pd.Series({'ticker' : self.instrument, 'ltp' : self.message['ltp'], 'cum_volume' : self.message['volume']}, 
                            name = self.timestamp))
        
        self.raw_data[self.instrument]['volume'] = self.raw_data[self.instrument]['cum_volume'].diff()
        
    def open_callback(self):
    
        self.socket_opened = True
        
    
    def start_live_feed(self):
    
        self.alice.start_websocket(subscribe_callback=self.get_ltp,
                          socket_open_callback=self.open_callback,
                          run_in_background=True)

        while(self.socket_opened==False):
            pass

        for key in self.ins_exc:
        
            self.alice.subscribe(self.alice.get_instrument_by_symbol(self.ins_exc[key]['exchange'], key), LiveFeedType.COMPACT)

            kite = Zerodha()
            kite.load_creds()
            kite.login()

            if (key[-3:] == 'FUT'):

                ins_kite = self.ins_exc[key]['exchange'] + ':' + key.split(' ')[0] + str(datetime.date.today().year)[2:] + key.split(' ')[1] + key.split(' ')[2]
                ins_kite_number = kite.quote(ins_kite)[ins_kite]['instrument_token']
                from_date = datetime.date.today() - datetime.timedelta(days = 5)
                to_date = datetime.date.today()
                interval = "minute"
                self.data[key] = pd.DataFrame(kite.historical_data(ins_kite_number, from_date, to_date, interval, continuous=False, oi=False))

            else:

                ins_kite = self.ins_exc[key]['exchange'] + ':' + key
                ins_kite_number = kite.quote(ins_kite)[ins_kite]['instrument_token']
                from_date = datetime.date.today() - datetime.timedelta(days = 5)
                to_date = datetime.date.today()
                interval = "minute"
                self.data[key] = pd.DataFrame(kite.historical_data(ins_kite_number, from_date, to_date, interval, continuous=False, oi=False))


            self.data[key]['datetime'] = self.data[key]['date']
            self.data[key]['ticker'] = key

            self.data[key]['date'] = self.data[key]['datetime'].apply(lambda x : x.date())
            self.data[key]['time'] = self.data[key]['datetime'].apply(lambda x : x.time())

            self.data[key] = self.data[key][['datetime','ticker','open','high','low','close','volume','date','time']]
            self.data[key]['datetime'] = self.data[key]['date'].apply(str) + self.data[key]['time'].apply(str)
            self.data[key]['datetime'] = self.data[key]['datetime'].apply(lambda x : datetime.datetime.strptime(x, '%Y-%m-%d%H:%M:%S'))
            self.data[key].set_index('datetime', inplace=True)
            
    @staticmethod
    def obtain_timedelta(timeframe):

        if timeframe[-1] == 'S':
            td = datetime.timedelta(seconds=int(timeframe[:-1]))

        elif timeframe[-1] == 'T':
            td = datetime.timedelta(minutes=int(timeframe[:-1]))

        elif timeframe[-3:].lower() == 'min':
            td = datetime.timedelta(minutes=int(timeframe[:-3]))

        elif timeframe[-1] == 'H':
            td = datetime.timedelta(hours=int(timeframe[:-1]))

        elif timeframe[-1] == 'D':
            td = datetime.timedelta(days=int(timeframe[:-1]))

        elif timeframe[-1] == 'W':
            td = datetime.timedelta(weeks=int(timeframe[:-1]))

        else:
            td = None

        return td
    
    def resample_data(self):
    
        self.thread_resample_run = True
        
        while self.thread_resample_run:

            for ins in self.instruments:
                
                if len(self.raw_data[ins]) == 0:

                    continue
                                                    
                temp = pd.DataFrame({'open' : self.raw_data[ins]['ltp'].resample(self.timeframe).first(),
                                     'high' : self.raw_data[ins]['ltp'].resample(self.timeframe).max(),
                                     'low' : self.raw_data[ins]['ltp'].resample(self.timeframe).min(),
                                     'close' : self.raw_data[ins]['ltp'].resample(self.timeframe).last(),
                                     'volume' : self.raw_data[ins]['volume'].resample(self.timeframe).sum()
                                    })

                temp['ticker'] = ins
                temp['date'] = temp.index.date
                temp['time'] = temp.index.time

                self.data[ins].at[temp.index[0]] = temp.iloc[0]
                
                if temp.index[-1] > self.data[ins].index[-1]:

                    previous_tick = self.data[ins].index[-1] + self.obtain_timedelta(self.timeframe)

                    self.raw_data[ins] = self.raw_data[ins][self.raw_data[ins].index > previous_tick]
    
    def start_thread(self):

        self.thread_resample = threading.Thread(target = self.resample_data)
        self.thread_resample.start()
        
    def terminate_thread(self):
            
        self.thread_resample_run = False
        self.thread_resample.join()