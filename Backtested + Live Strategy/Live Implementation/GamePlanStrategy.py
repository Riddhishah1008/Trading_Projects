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
from fyers_api import accessToken
from jugaad_trader import Zerodha

class GamePlan:
    
    def __init__(self, instrument, exchange, data, quantity):

        self.instrument = instrument
        self.exchange = exchange
        self.data = data
        self.position_size = quantity
        self.percentage_padding = 0.02
        self.capital = 0

        if self.data.iloc[-1]['close'] < 500:
            self.stoploss = round(self.data.iloc[-1]['close']/500, 1)
            
        elif self.instrument[:5] == 'NIFTY':
            self.stoploss = 10
            
        elif self.instrument[:9] == 'BANKNIFTY':
            self.stoploss = 40
        
        else:
            self.stoploss = round(self.data.iloc[-1]['close']/500)

        self.today = pd.Timestamp(datetime.date.today())
        
        if self.exchange == 'MCX':
            self.market_close = datetime.time(hour=23, minute=30)
        else:
            self.market_close = datetime.time(hour=15, minute=30)
        
        self.df = self.data.copy()
        self.prices_calculated_flag = False
        self.long_position_flag = False
        self.long_target_1_flag = False
        self.long_target_2_flag = False
        self.short_position_flag = False
        self.short_target_1_flag = False
        self.short_target_2_flag = False
        
    @staticmethod
    def price_range(current_price, price_reference, percentage):

        return ((price_reference * (1 - percentage/100) < current_price) & 
                    (current_price < price_reference * (1 + percentage/100)))
    
    def send_signals(self):

        self.thread_send_signals = threading.Thread(target = self.send_signals_for_thread)
        self.thread_send_signals.start()
        
    def terminate_signals(self):
            
        self.signals_run_thread_flag = False
 
    def create_price_levels(self):
        
        self.index = self.data.index[-1]
        self.row = self.data.iloc[-1]

        if ((self.index.date() == self.today) & 
           (self.index.time() > datetime.time(hour=9, minute=30)) & 
           (self.prices_calculated_flag == False)):

            self.candle = self.data[(self.data['time'] >= datetime.time(hour=9, minute=15)) & 
                                                              (self.data['time'] <= datetime.time(hour=9, minute=30)) &
                                                              (self.data['date'] == self.today)]

            self.high = self.candle['high'].max()
            self.low = self.candle['low'].min()

            self.diff = round(self.high - self.low, 3)
            self.atp = round((self.high + self.low) / 2, 3)

            self.derived = round(self.diff * 0.618, 3)

            self.buy = round(self.atp + self.stoploss, 3)
            self.sell = round(self.atp - self.stoploss, 3)

            self.buy_momentum = round(self.atp + self.derived, 3)
            self.sell_momentum = round(self.atp - self.derived, 3)

            self.long_target_1 = round(self.buy_momentum + self.diff, 3)
            self.long_target_2 = round(self.long_target_1 + self.diff, 3)

            self.short_target_1 = round(self.sell_momentum - self.diff, 3)
            self.short_target_2 = round(self.short_target_1 - self.diff, 3)

            self.price_levels = {
                                    'stoploss' : self.stoploss,
                                    'high': self.high,
                                    'low': self.low,
                                    'buy': self.buy,
                                    'sell': self.sell,
                                    'buy_momentum': self.buy_momentum,
                                    'sell_momentum': self.sell_momentum,
                                    'long_target_1': self.long_target_1,
                                    'long_target_2': self.long_target_2,
                                    'short_target_1': self.short_target_1,
                                    'short_target_2': self.short_target_2
                                }

            self.prices_calculated_flag = True
 
    def send_signals_for_thread(self):

        self.signals_run_thread_flag = True
        
        while self.signals_run_thread_flag:
            
            self.index = self.data.index[-1]
            self.row = self.data.iloc[-1]
            
            if ((self.index.date() == self.today) &
                (self.index.time() > datetime.time(hour=9, minute=30))):
                
                if self.prices_calculated_flag == False:
                    self.create_price_levels()

                self.df.loc[self.index] = self.row
                self.df['cci'] = talib.CCI(self.df['high'],
                                      self.df['low'],
                                      self.df['close'],
                                      timeperiod=369)

                self.ltp = self.df.iloc[-1]['close']
                self.cci = self.df.iloc[-1]['cci']
                
                self.price_flags = {
                                        'long_position_flag': self.long_position_flag,
                                        'long_target_1_flag': self.long_target_1_flag,
                                        'long_target_2_flag': self.long_target_2_flag,
                                        'short_position_flag': self.short_position_flag,
                                        'short_target_1_flag': self.short_target_1_flag,
                                        'short_target_2_flag': self.short_target_2_flag
                                    }

                if (self.long_position_flag | self.short_position_flag) == False:
   
                    
                    if self.price_range(self.ltp, self.buy, self.percentage_padding) & (self.cci > 20):

                        self.long_position_flag = True
                        self.long_target_1_flag = False
                        self.long_target_2_flag = False
                        self.capital = self.capital - (self.position_size * self.ltp)
                        telegram_bot.send(f'{self.instrument}\n{self.index}\nLONG ENTRY - Price : {self.ltp} \nGameplan Buy Price : {self.buy}')
                        print(f'{self.instrument}\n{self.index}\nLONG ENTRY - Price : {self.ltp} \nGameplan Buy Price : {self.buy}')
                        print('______________________________________________')

                    elif self.price_range(self.ltp, self.sell, self.percentage_padding) & (self.cci < -20):

                        self.short_position_flag = True
                        self.short_target_1_flag = False
                        self.short_target_2_flag = False
                        self.capital = self.capital + (self.position_size * self.ltp)
                        telegram_bot.send(f'{self.instrument}\n{self.index}\nSHORT ENTRY - Price : {self.ltp} \nGameplan Sell Price : {self.sell}')
                        print(f'{self.instrument}\n{self.index}\nSHORT ENTRY - Price : {self.ltp} \nGameplan Sell Price : {self.sell}')
                        print('______________________________________________')

                if self.long_position_flag:
                    
                    
                    if (self.ltp > self.long_target_1) & (self.long_target_1_flag == False):

                        self.long_target_1_flag = True
                        self.capital = self.capital + (self.position_size/2 * self.ltp)
                        telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT LONG TARGET 1 - Price : {self.ltp} \nGameplan Target 1 Price : {self.long_target_1}')
                        print(f'{self.instrument}\n{self.index}\nHIT LONG TARGET 1 - Price : {self.ltp} \nGameplan Target 1 Price : {self.long_target_1}')
                        print('______________________________________________')

                    elif (self.ltp > self.long_target_2) & (self.long_target_2_flag == False) & (self.long_target_1_flag == True):

                        self.long_target_2_flag = True
                        self.long_position_flag = False
                        self.long_target_1_flag = False
                        self.long_target_2_flag = False
                        self.short_position_flag = False
                        self.short_target_1_flag = False
                        self.short_target_2_flag = False
                        self.capital = self.capital + (self.position_size/2 * self.ltp)
                        telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT LONG TARGET 2 - Price : {self.ltp} \nGameplan Target 2 Price : {self.long_target_2}')
                        print(f'{self.instrument}\n{self.index}\nHIT LONG TARGET 2 - Price : {self.ltp} \nGameplan Target 2 Price : {self.long_target_2} \nCapital : {self.capital}')
                        print('______________________________________________')

                    elif (self.ltp < self.buy_momentum) & (self.long_target_1_flag == True) & (self.long_target_2_flag == False):

                        self.long_position_flag = False
                        self.long_target_1_flag = False
                        self.long_target_2_flag = False
                        self.short_position_flag = False
                        self.short_target_1_flag = False
                        self.short_target_2_flag = False
                        self.capital = self.capital + (self.position_size/2 * self.ltp)
                        telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT STOP LOSS AFTER Target 1 - Price : {self.ltp} \nGameplan Buy Momentum : {self.buy_momentum}')
                        print(f'{self.instrument}\n{self.index}\nHIT STOP LOSS AFTER Target 1 - Price : {self.ltp} \nGameplan Buy Momentum : {self.buy_momentum}')
                        print('______________________________________________')

                    elif self.ltp < self.sell:

                        if self.long_target_1_flag:

                            self.long_position_flag = False
                            self.long_target_1_flag = False
                            self.long_target_2_flag = False
                            self.short_position_flag = False
                            self.short_target_1_flag = False
                            self.short_target_2_flag = False
                            self.capital = self.capital + (self.position_size/2 * self.ltp)
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT STOP LOSS - Price : {self.ltp} \nGameplan Sell Price : {self.sell}')
                            print(f'{self.instrument}\n{self.index}\n HIT STOP LOSS - Price : {self.ltp} \nGameplan Sell Price : {self.sell}')
                            print('______________________________________________')

                        else:

                            self.long_position_flag = False
                            self.long_target_1_flag = False
                            self.long_target_2_flag = False
                            self.short_position_flag = False
                            self.short_target_1_flag = False
                            self.short_target_2_flag = False
                            self.capital = self.capital + (self.position_size * self.ltp)
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT STOP LOSS - Price : {self.ltp} \nGameplan Sell Price : {self.sell}')
                            print(f'{self.instrument}\n{self.index}\nHIT STOP LOSS - Price : {self.ltp} \nGameplan Sell Price : {self.sell} \nCapital : {self.capital}')
                            print('______________________________________________')

                        if self.cci < -20:

                            self.short_position_flag = True
                            self.capital = self.capital + (self.position_size * self.ltp)
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT SHORT ENTRY - Price : {self.ltp} \nGameplan Sell Price : {self.sell}')
                            print(f'{self.instrument}\n{self.index}\nHIT SHORT ENTRY - Price : {self.ltp} \nGameplan Buy Price : {self.sell}')
                            print('______________________________________________')

                if self.short_position_flag:                    

                    if (self.ltp < self.short_target_1) & (self.short_target_1_flag == False):

                        self.short_target_1_flag = True
                        self.capital = self.capital - (self.position_size/2 * self.ltp)
                        telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT SHORT TARGET 1 - Price : {self.ltp} \nGameplan Target 1 Price : {self.short_target_1}')
                        print(f'{self.instrument}\n{self.index}\nHIT SHORT TARGET 1 - Price : {self.ltp} \nGameplan Target 1 Price : {self.short_target_1}')
                        print('______________________________________________')

                    elif (self.ltp < self.short_target_2) & (self.short_target_2_flag == False) & (self.short_target_1_flag == True):

                        self.short_target_2_flag = True
                        self.long_position_flag = False
                        self.long_target_1_flag = False
                        self.long_target_2_flag = False
                        self.short_position_flag = False
                        self.short_target_1_flag = False
                        self.short_target_2_flag = False
                        self.capital = self.capital - (self.position_size/2 * self.ltp)
                        telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT SHORT TARGET 2 - Price : {self.ltp} \nGameplan Target 2 Price : {self.short_target_2}')
                        print(f'{self.instrument}\n{self.index}\nHIT SHORT TARGET 2 - Price : {self.ltp} \nGameplan Target 2 Price : {self.short_target_2} \nCapital : {self.capital}')
                        print('______________________________________________')

                    elif (self.ltp > self.sell_momentum) & (self.short_target_1_flag == True) & (self.short_target_2_flag == False):

                        self.long_position_flag = False
                        self.long_target_1_flag = False
                        self.long_target_2_flag = False
                        self.short_position_flag = False
                        self.short_target_1_flag = False
                        self.short_target_2_flag = False
                        self.capital = self.capital - (self.position_size/2 * self.ltp)
                        telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT STOP LOSS - Price : {self.ltp} \nGameplan Buy Price : {self.sell_momentum}')
                        print(f'{self.instrument}\n{self.index}\nHIT STOP LOSS - Price : {self.ltp} \nGameplan Buy Price : {self.sell_momentum}')
                        print('______________________________________________')

                    elif self.ltp > self.buy:

                        if self.short_target_1_flag:

                            self.long_position_flag = False
                            self.long_target_1_flag = False
                            self.long_target_2_flag = False
                            self.short_position_flag = False
                            self.short_target_1_flag = False
                            self.short_target_2_flag = False
                            self.capital = self.capital - (self.position_size/2 * self.ltp)
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT STOP LOSS - Price : {self.ltp} \nGameplan Buy Price : {self.buy}')
                            print(f'{self.instrument}\n{self.index}\nHIT STOP LOSS - Price : {self.ltp} \nGameplan Buy Price : {self.buy} \nCapital : {self.capital}')
                            print('______________________________________________')

                        else:

                            self.long_position_flag = False
                            self.long_target_1_flag = False
                            self.long_target_2_flag = False
                            self.short_position_flag = False
                            self.short_target_1_flag = False
                            self.short_target_2_flag = False
                            self.capital = self.capital - (self.position_size * self.ltp)
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT STOP LOSS - Price : {self.ltp} \nGameplan Sell Price : {self.buy}')
                            print(f'{self.instrument}\n{self.index}\nHIT STOP LOSS - Price : {self.ltp} \nGameplan Buy Price : {self.buy} \nCapital : {self.capital}')
                            print('______________________________________________')

                        if self.cci > 20:

                            self.long_position_flag = True
                            self.capital = self.capital - (self.position_size * self.ltp)
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nLONG ENTRY - Price : {self.ltp} \nGameplan Buy Price : {self.buy}')
                            print(f'{self.instrument}\n{self.index}\nHIT LONG ENTRY - Price : {self.ltp} \nGameplan Buy Price : {self.buy}')
                            print('______________________________________________')


                if (((self.long_position_flag | self.short_position_flag) == True) & (self.index.time() >= datetime.time(hour=self.market_close.hour, minute=self.market_close.minute-5))):

                    if self.long_position_flag:

                        if self.long_target_1_flag:

                            self.long_position_flag = False
                            self.long_target_1_flag = False
                            self.long_target_2_flag = False
                            self.short_position_flag = False
                            self.short_target_1_flag = False
                            self.short_target_2_flag = False
                            self.capital = self.capital + (self.position_size/2 * self.ltp)
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nEND OF DAY CLOSING LONG POSITION - Price : {self.ltp}')
                            print(f'{self.instrument}\n{self.index}\nEND OF DAY CLOSING LONG POSITION - Price : {self.ltp} \nCapital : {self.capital}')
                            print('______________________________________________')

                        else:

                            self.long_position_flag = False
                            self.long_target_1_flag = False
                            self.long_target_2_flag = False
                            self.short_position_flag = False
                            self.short_target_1_flag = False
                            self.short_target_2_flag = False
                            self.capital = self.capital + (self.position_size * self.ltp)
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nEND OF DAY CLOSING LONG POSITION - Price : {self.ltp}')
                            print(f'{self.instrument}\n{self.index}\nEND OF DAY CLOSING LONG POSITION - Price : {self.ltp} \nCapital : {self.capital}')
                            print('______________________________________________')


                    if self.short_position_flag:

                        if self.short_target_1_flag:

                            self.long_position_flag = False
                            self.long_target_1_flag = False
                            self.long_target_2_flag = False
                            self.short_position_flag = False
                            self.short_target_1_flag = False
                            self.short_target_2_flag = False
                            self.capital = self.capital - (self.position_size/2 * self.ltp)
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nEND OF DAY CLOSING SHORT POSITION- Price : {self.ltp}')
                            print(f'{self.instrument}\n{self.index}\nEND OF DAY CLOSING SHORT POSITION - Price : {self.ltp} \nCapital : {self.capital}')
                            print('______________________________________________')

                        else:

                            self.long_position_flag = False
                            self.long_target_1_flag = False
                            self.long_target_2_flag = False
                            self.short_position_flag = False
                            self.short_target_1_flag = False
                            self.short_target_2_flag = False
                            self.capital = self.capital - (self.position_size * ltp)
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nEND OF DAY CLOSING SHORT POSITION- Price : {self.ltp}')
                            print(f'{self.instrument}\n{self.index}\nEND OF DAY CLOSING SHORT POSITION - Price : {self.ltp} \nCapital : {self.capital}')
                            print('______________________________________________')
                    
                    self.signals_run_thread_flag = False                            
            