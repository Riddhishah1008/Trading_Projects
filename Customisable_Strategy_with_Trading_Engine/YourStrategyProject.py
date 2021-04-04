# ------------------------------------------------------------------------
# This module defines your strategy and send you signals for the same
# Here it is assumed that you resample data from Alice Blue to 1 minute
# Create price levels based on the first 15 minutes
# You buy if the price is at the determined buy price 
# and the stop loss is the determined sell price
# Similarly sell if the price is at the determined sell price 
# and the stop loss is the determined buy price
# You cover half of your positions at the first target 
# and the other half at the second target
# ------------------------------------------------------------------------


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
from AliceBlueDataProject import AmadeusData_AliceBlue

# -----------------------------------------------------------
# Create a class and define your strategy 
# -----------------------------------------------------------

class YourStrategy:
    
    # -----------------------------------------------------------
    # Init method accepts instrument symbol, exchange, the live updated dataframe and quantity as inputs
    # -----------------------------------------------------------
        
    def __init__(self, instrument, exchange, data, quantity):

        # Set instrument input as a class attribute
        self.instrument = instrument
        
        # Set exchange input as a class attribute
        self.exchange = exchange
        
        # Set dataframe input as a class attribute
        self.data = data
        
        # Set quantity input as a class attribute
        self.position_size = quantity
        
        # Create a class attribute to store percentage padding
        # Refer price_range method to understand requirement
        self.percentage_padding = 0.02
        
        # Initial capital is created as a class attribute and is set to 0
        self.capital = 0
        
        # Save today's date as a class attribute
        self.today = pd.Timestamp(datetime.date.today())
        
        # Set market close time
        # If the exchange is commodities
        if self.exchange == 'MCX':
            
            # Set market close time to 11:30 PM
            self.market_close = datetime.time(hour=23, minute=30)
            
        # If any other exchange
        else:
            
            # Set market close time to 3:30 PM
            self.market_close = datetime.time(hour=15, minute=30)
        
        # Create a copy of the data passed as argument
        self.df = data.copy()
        
        # Create a flag to check if the price levels for the day are calculated and initialise it to False
        self.prices_calculated_flag = False
        
        # Create a flag to see if long position is entered and initialise it to False
        self.long_position_flag = False
        
        # Create a flag to see if long target 1 is achieved and initialise it to False
        self.long_target_1_flag = False
        
        # Create a flag to see if long target 2 is achieved and initialise it to False
        self.long_target_2_flag = False
        
        # Create a flag to see if short position is entered and initialise it to False
        self.short_position_flag = False
        
        # Create a flag to see if short target 1 is achieved and initialise it to False
        self.short_target_1_flag = False
        
        # Create a flag to see if short target 2 is achieved and initialise it to False
        self.short_target_2_flag = False
        
        # Set the flag to check thread run to True
        self.signals_run_thread_flag = True
     
    
    # -----------------------------------------------------------
    # Create a static method to calculate price range around a 
    # particular price taking the percentage padding as input
    # -----------------------------------------------------------
    
    @staticmethod
    def price_range(current_price, price_reference, percentage):

        # Return True if the price is within the percentage padding price range
        # Else return False
        return ((price_reference * (1 - percentage/100) < current_price) & 
                    (current_price < price_reference * (1 + percentage/100)))
    
    
    # -----------------------------------------------------------
    # Create price levels using the first 15 minutes candle
    # -----------------------------------------------------------
    
    def create_price_levels(self):
        
        # Save the index of the last row of the live data feed dataframe as a class attribute
        self.index = self.data.index[-1]

        # If the index attribute's date is today and it is past 9:30 PM and prices_calculated_flag is still False
        if ((self.index.date() == self.today) & 
           (self.index.time() > datetime.time(hour=9, minute=30)) & 
           (self.prices_calculated_flag == False)):
 
            # Save the first 15 minutes candle of today into a class attribute dataframe candle
            self.candle = self.data[(self.data['time'] >= datetime.time(hour=9, minute=15)) & 
                                                              (self.data['time'] <= datetime.time(hour=9, minute=30)) &
                                                              (self.data['date'] == self.today)]

            # Save the highest high as a class attribute
            self.high = self.candle['high'].max()
            # Save the lowest low as a class attribute
            self.low = self.candle['low'].min()

            # Calculate the average of high and low and save it as a class attribute
            self.avg = round((self.high + self.low) / 2, 3)

            # Create your own buy price
            # Here as an example it is high + avg price
            self.buy = round(self.high + self.avg, 3)
            
            # Create your own sell price
            # Here as an example it is high - avg price
            self.sell = round(self.low - self.avg, 3)

            # Create your own long target prices
            # Here as an example long target 1 is buy price + avg price
            self.long_target_1 = round(self.buy + self.avg, 3)
            
            # Here as an example long target 2 is long target 1 + avg price
            self.long_target_2 = round(self.long_target_1 + self.avg, 3)

            # Create your own short target prices
            # Here as an example short target 1 is sell price - avg price
            self.short_target_1 = round(self.sell - self.avg, 3)
            
            # Here as an example short target 2 is short target 1 - avg price
            self.short_target_2 = round(self.short_target_1 - self.avg, 3)

            # Save all the calculated prices in a dictionary to view them all at once during running
            self.price_levels = {
                                    'high': self.high,
                                    'low': self.low,
                                    'buy': self.buy,
                                    'sell': self.sell,
                                    'long_target_1': self.long_target_1,
                                    'long_target_2': self.long_target_2,
                                    'short_target_1': self.short_target_1,
                                    'short_target_2': self.short_target_2
                                }

            # Set prices_calculated_flag to True
            self.prices_calculated_flag = True
 
    
    # -----------------------------------------------------------
    # Send signals according to price levels calculated
    # -----------------------------------------------------------
    
    def send_signals_for_thread(self):

        # Run while the flag to check thread run is True
        while self.signals_run_thread_flag:
            
            # Save the index of the last row of the live data feed dataframe as a class attribute
            self.index = self.data.index[-1]

            # Save the last row of the live data feed dataframe as a class attribute
            self.row = self.data.iloc[-1]
            
            # If the date matches today and it is past 9:30 PM
            if ((self.index.date() == self.today) &
                (self.index.time() > datetime.time(hour=9, minute=30))):
                
                # If the prices_calculated_flag is False
                if self.prices_calculated_flag == False:
                    
                    # Calculate the prices
                    self.create_price_levels()

                # Append the last row at the same index as the live data to df dataframe
                self.df.loc[self.index] = self.row
                
                # Add any indicator of your choice
                # Here as an example RSI of 14 periods has been taken on the close
                self.df['rsi'] = talib.RSI(self.df['close'], timeperiod = 14)

                # Store the last ticker price in class attribute ltp
                self.ltp = self.df.iloc[-1]['close']
                
                # Store the last RSI value in class attribute rsi
                self.rsi = self.df.iloc[-1]['rsi']
                
                # Save all the price flags in a dictionary to view them all at once during running
                self.price_flags = {
                                        'long_position_flag': self.long_position_flag,
                                        'long_target_1_flag': self.long_target_1_flag,
                                        'long_target_2_flag': self.long_target_2_flag,
                                        'short_position_flag': self.short_position_flag,
                                        'short_target_1_flag': self.short_target_1_flag,
                                        'short_target_2_flag': self.short_target_2_flag
                                    }

                # If we are neither long nor short
                if (self.long_position_flag | self.short_position_flag) == False:
   
                    # And price is within the percentage padding range of 0.02% of the buy price and rsi is above 60
                    if self.price_range(self.ltp, self.buy, self.percentage_padding) & (self.rsi > 60):

                        # Long position flag is set to True
                        self.long_position_flag = True
                    
                        # Long target 1 flag is set to False to make sure there is no discrepancy as we enter long
                        self.long_target_1_flag = False
                        
                        # Long target 2 flag is set to False to make sure there is no discrepancy as we enter long
                        self.long_target_2_flag = False
                        
                        # We reduce our capital by an amount equal to (the price bought at) * (quantity bought)
                        self.capital = self.capital - (self.position_size * self.ltp)
                        
                        # Send a telegram message specifying the instrument symbol, datetime stamp of order, 
                        # the price filled at and the price set by your strategy's formula
                        telegram_bot.send(f'{self.instrument}\n{self.index}\nLONG ENTRY - Price : {self.ltp} \nYour Strategy Buy Price : {self.buy}')
                        
                        # Print the same message
                        print(f'{self.instrument}\n{self.index}\nLONG ENTRY - Price : {self.ltp} \nYour Strategy Buy Price : {self.buy}')
                        
                        # Print line for readability
                        print('______________________________________________')

                    # Else if price is within the percentage padding range of 0.02% of the sell price and rsi is below 40
                    elif self.price_range(self.ltp, self.sell, self.percentage_padding) & (self.rsi < 40):

                        # Short position flag is set to True
                        self.short_position_flag = True
                        
                        # Short target 1 flag is set to False to make sure there is no discrepancy as we enter short
                        self.short_target_1_flag = False
                        
                        # Short target 2 flag is set to False to make sure there is no discrepancy as we enter short
                        self.short_target_2_flag = False
                        
                        # We increase our capital by an amount equal to (the price bought at) * (quantity bought)
                        self.capital = self.capital + (self.position_size * self.ltp)
                        
                        # Send a telegram message specifying the instrument symbol, datetime stamp of order, 
                        # the price filled at and the price set by your strategy's formula
                        telegram_bot.send(f'{self.instrument}\n{self.index}\nSHORT ENTRY - Price : {self.ltp} \nYour Strategy Sell Price : {self.sell}')
                        
                        # Print the same message
                        print(f'{self.instrument}\n{self.index}\nSHORT ENTRY - Price : {self.ltp} \nYour Strategy Sell Price : {self.sell}')
                        
                        # Print line for readability
                        print('______________________________________________')

                # If we are in long position
                if self.long_position_flag:
                    
                    # And if price goes above long target 1 while the target 1 flag is still False
                    if (self.ltp > self.long_target_1) & (self.long_target_1_flag == False):

                        # Set the Long Target 1 flag to True
                        self.long_target_1_flag = True
                        
                        # We increase our capital by an amount equal to (the price bought at) * (quantity bought/2)
                        # Because we cover half of our position size at first target
                        self.capital = self.capital + (self.position_size/2 * self.ltp)
                        
                        # Send a telegram message specifying the instrument symbol, datetime stamp of order, 
                        # the price filled at and the price set by your strategy's formula
                        telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT LONG TARGET 1 - Price : {self.ltp} \nYour Strategy Target 1 Price : {self.long_target_1}')
                        
                        # Print the same message
                        print(f'{self.instrument}\n{self.index}\nHIT LONG TARGET 1 - Price : {self.ltp} \nYour Strategy Target 1 Price : {self.long_target_1}')
                        
                        # Print line for readability
                        print('______________________________________________')

                    # Else if price goes above long target 2 while the target 2 flag is still False but target 1 is True
                    elif (self.ltp > self.long_target_2) & (self.long_target_2_flag == False) & (self.long_target_1_flag == True):

                        # Set the Long Target 2 flag to True
                        self.long_target_2_flag = True
                        
                        # Set all flags to False as we exit our long position
                        # Set the long position flag to False
                        self.long_position_flag = False
                        
                        # Set the long target 1 flag to False
                        self.long_target_1_flag = False
                        
                        # Set the long target 2 flag to False
                        self.long_target_2_flag = False
                        
                        # Set the short position flag to False
                        self.short_position_flag = False
                        
                        # Set the short target 1 flag to False
                        self.short_target_1_flag = False
                        
                        # Set the short target 2 flag to False
                        self.short_target_2_flag = False
                        
                        # We increase our capital by an amount equal to (the price bought at) * (quantity bought/2)
                        # Because we cover the other half of our position size at second target
                        self.capital = self.capital + (self.position_size/2 * self.ltp)
                        
                        # Send a telegram message specifying the instrument symbol, datetime stamp of order, 
                        # the price filled at and the price set by your strategy's formula
                        telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT LONG TARGET 2 - Price : {self.ltp} \nYour Strategy Target 2 Price : {self.long_target_2}')
                        
                        # Print the same message
                        print(f'{self.instrument}\n{self.index}\nHIT LONG TARGET 2 - Price : {self.ltp} \nYour Strategy Target 2 Price : {self.long_target_2} \nCapital : {self.capital}')
                        
                        # Print line for readability
                        print('______________________________________________')

                    # Else if the prices go below our sell mark which acts as our stop loss
                    elif self.ltp < self.sell:

                        # If long target 1 has been achieved
                        if self.long_target_1_flag:

                            # We cover our other half of open positions and set all flags to False
                            # Set the long position flag to False
                            self.long_position_flag = False

                            # Set the long target 1 flag to False
                            self.long_target_1_flag = False

                            # Set the long target 2 flag to False
                            self.long_target_2_flag = False

                            # Set the short position flag to False
                            self.short_position_flag = False

                            # Set the short target 1 flag to False
                            self.short_target_1_flag = False

                            # Set the short target 2 flag to False
                            self.short_target_2_flag = False
                            
                            # We increase our capital by an amount equal to (the price bought at) * (quantity bought/2)
                            # Because we cover the other half of our position size at stop loss post target 1 being achieved
                            self.capital = self.capital + (self.position_size/2 * self.ltp)
                            
                            # Send a telegram message specifying the instrument symbol, datetime stamp of order, 
                            # the price filled at and the price set by your strategy's formula
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT STOP LOSS - Price : {self.ltp} \nYour Strategy Sell Price : {self.sell}')
                            
                            # Print the same message
                            print(f'{self.instrument}\n{self.index}\n HIT STOP LOSS - Price : {self.ltp} \nYour Strategy Sell Price : {self.sell}')
                            
                            # Print line for readability
                            print('______________________________________________')

                        # If long target 1 has not been achieved
                        else:

                            # We cover all of our open positions and set all flags to False
                            # Set the long position flag to False
                            self.long_position_flag = False

                            # Set the long target 1 flag to False
                            self.long_target_1_flag = False

                            # Set the long target 2 flag to False
                            self.long_target_2_flag = False

                            # Set the short position flag to False
                            self.short_position_flag = False

                            # Set the short target 1 flag to False
                            self.short_target_1_flag = False

                            # Set the short target 2 flag to False
                            self.short_target_2_flag = False
                            
                            # We increase our capital by an amount equal to (the price bought at) * (quantity bought)
                            self.capital = self.capital + (self.position_size * self.ltp)
                            
                            # Send a telegram message specifying the instrument symbol, datetime stamp of order, 
                            # the price filled at and the price set by your strategy's formula
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT STOP LOSS - Price : {self.ltp} \nYour Strategy Sell Price : {self.sell}')
                            
                            # Print the same message
                            print(f'{self.instrument}\n{self.index}\nHIT STOP LOSS - Price : {self.ltp} \nYour Strategy Sell Price : {self.sell} \nCapital : {self.capital}')
                            
                            # Print line for readability
                            print('______________________________________________')

                        # If the RSI is below 40 while prices are below the sell price
                        if self.rsi < 40:

                            # Enter a short position
                            self.short_position_flag = True
                            
                            # We increase our capital by an amount equal to (the price bought at) * (quantity bought)
                            self.capital = self.capital + (self.position_size * self.ltp)
                            
                            # Send a telegram message specifying the instrument symbol, datetime stamp of order, 
                            # the price filled at and the price set by your strategy's formula
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT SHORT ENTRY - Price : {self.ltp} \nYour Strategy Sell Price : {self.sell}')
                            
                            # Print the same message
                            print(f'{self.instrument}\n{self.index}\nHIT SHORT ENTRY - Price : {self.ltp} \nYour Strategy Buy Price : {self.sell}')
                            
                            # Print line for readability
                            print('______________________________________________')

                # If we are in short position
                if self.short_position_flag:                    

                    # And if price goes below short target 1 while the target 1 flag is still False
                    if (self.ltp < self.short_target_1) & (self.short_target_1_flag == False):

                        # Set short target 1 flag to True
                        self.short_target_1_flag = True
                        
                        # We reduce our capital by an amount equal to (the price bought at) * (quantity bought/2)
                        # Because we cover half of our position size at first target
                        self.capital = self.capital - (self.position_size/2 * self.ltp)
                        
                        # Send a telegram message specifying the instrument symbol, datetime stamp of order, 
                        # the price filled at and the price set by your strategy's formula
                        telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT SHORT TARGET 1 - Price : {self.ltp} \nYour Strategy Target 1 Price : {self.short_target_1}')
                        
                        # Print the same message
                        print(f'{self.instrument}\n{self.index}\nHIT SHORT TARGET 1 - Price : {self.ltp} \nYour Strategy Target 1 Price : {self.short_target_1}')
                        
                        # Print line for readability
                        print('______________________________________________')

                    # Else if price goes below short target 2 while the target 2 flag is still False but target 1 is True
                    elif (self.ltp < self.short_target_2) & (self.short_target_2_flag == False) & (self.short_target_1_flag == True):

                        # We set the short target 2 flag to True
                        self.short_target_2_flag = True
                        
                        # Set all other flags to False as we exit our short position
                        # Set the long position flag to False
                        self.long_position_flag = False
                        
                        # Set the long target 1 flag to False
                        self.long_target_1_flag = False
                        
                        # Set the long target 2 flag to False
                        self.long_target_2_flag = False
                        
                        # Set the short position flag to False
                        self.short_position_flag = False
                        
                        # Set the short target 1 flag to False
                        self.short_target_1_flag = False
                        
                        # Set the short target 2 flag to False
                        self.short_target_2_flag = False
                        
                        # We reduce our capital by an amount equal to (the price bought at) * (quantity bought/2)
                        # Because we cover the other half of our position size at second target
                        self.capital = self.capital - (self.position_size/2 * self.ltp)
                        
                        # Send a telegram message specifying the instrument symbol, datetime stamp of order, 
                        # the price filled at and the price set by your strategy's formula
                        telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT SHORT TARGET 2 - Price : {self.ltp} \nYour Strategy Target 2 Price : {self.short_target_2}')
                        
                        # Print the same message
                        print(f'{self.instrument}\n{self.index}\nHIT SHORT TARGET 2 - Price : {self.ltp} \nYour Strategy Target 2 Price : {self.short_target_2} \nCapital : {self.capital}')
                        
                        # Print line for readability
                        print('______________________________________________')

                    # Else if the prices go above our buy mark which acts as our stop loss
                    elif self.ltp > self.buy:

                        # If short target 1 has been achieved
                        if self.short_target_1_flag:

                            # We cover our other half of open positions and set all flags to False
                            # Set the long position flag to False
                            self.long_position_flag = False

                            # Set the long target 1 flag to False
                            self.long_target_1_flag = False

                            # Set the long target 2 flag to False
                            self.long_target_2_flag = False

                            # Set the short position flag to False
                            self.short_position_flag = False

                            # Set the short target 1 flag to False
                            self.short_target_1_flag = False

                            # Set the short target 2 flag to False
                            self.short_target_2_flag = False
                            
                            # We decrease our capital by an amount equal to (the price bought at) * (quantity bought/2)
                            # Because we cover the other half of our position size at stop loss post target 1 being achieved
                            self.capital = self.capital - (self.position_size/2 * self.ltp)
                            
                            # Send a telegram message specifying the instrument symbol, datetime stamp of order, 
                            # the price filled at and the price set by your strategy's formula
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT STOP LOSS - Price : {self.ltp} \nYour Strategy Buy Price : {self.buy}')
                            
                            # Print the same message
                            print(f'{self.instrument}\n{self.index}\nHIT STOP LOSS - Price : {self.ltp} \nYour Strategy Buy Price : {self.buy} \nCapital : {self.capital}')
                            
                            # Print line for readability
                            print('______________________________________________')

                        # If short target 1 has not been achieved
                        else:

                            # We cover all of our open positions and set all flags to False
                            # Set the long position flag to False
                            self.long_position_flag = False

                            # Set the long target 1 flag to False
                            self.long_target_1_flag = False

                            # Set the long target 2 flag to False
                            self.long_target_2_flag = False

                            # Set the short position flag to False
                            self.short_position_flag = False

                            # Set the short target 1 flag to False
                            self.short_target_1_flag = False

                            # Set the short target 2 flag to False
                            self.short_target_2_flag = False
                            
                            # We decrease our capital by an amount equal to (the price bought at) * (quantity bought)
                            self.capital = self.capital - (self.position_size * self.ltp)
                            
                            # Send a telegram message specifying the instrument symbol, datetime stamp of order, 
                            # the price filled at and the price set by your strategy's formula
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nHIT STOP LOSS - Price : {self.ltp} \nYour Strategy Sell Price : {self.buy}')
                            
                            # Print the same message
                            print(f'{self.instrument}\n{self.index}\nHIT STOP LOSS - Price : {self.ltp} \nYour Strategy Buy Price : {self.buy} \nCapital : {self.capital}')
                            
                            # Print line for readability
                            print('______________________________________________')

                        # If the RSI is above 60 while prices are above the buy price
                        if self.rsi > 60:

                            # Enter a long position
                            self.long_position_flag = True
                            
                            # We decrease our capital by an amount equal to (the price bought at) * (quantity bought)
                            self.capital = self.capital - (self.position_size * self.ltp)
                            
                            # Send a telegram message specifying the instrument symbol, datetime stamp of order, 
                            # the price filled at and the price set by your strategy's formula
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nLONG ENTRY - Price : {self.ltp} \nYour Strategy Buy Price : {self.buy}')
                            
                            # Print the same message
                            print(f'{self.instrument}\n{self.index}\nHIT LONG ENTRY - Price : {self.ltp} \nYour Strategy Buy Price : {self.buy}')
                            
                            # Print line for readability
                            print('______________________________________________')


                # If we are in either long or short position post 3:25 PM
                if (((self.long_position_flag | self.short_position_flag) == True) & (self.index.time() >= datetime.time(hour=15, minute=25))):

                    # If we are long
                    if self.long_position_flag:

                        # And target 1 has been achieved
                        if self.long_target_1_flag:

                            # We cover the other half of our open positions and set all flags to False
                            # Set the long position flag to False
                            self.long_position_flag = False

                            # Set the long target 1 flag to False
                            self.long_target_1_flag = False

                            # Set the long target 2 flag to False
                            self.long_target_2_flag = False

                            # Set the short position flag to False
                            self.short_position_flag = False

                            # Set the short target 1 flag to False
                            self.short_target_1_flag = False

                            # Set the short target 2 flag to False
                            self.short_target_2_flag = False
                            
                            # We increase our capital by an amount equal to (the price bought at) * (quantity bought/2)
                            # Because we cover the other half of our position size at stop loss post target 1 being achieved
                            self.capital = self.capital + (self.position_size/2 * self.ltp)
                            
                            # Send a telegram message specifying the instrument symbol, datetime stamp of order, 
                            # the price filled at and the price set by your strategy's formula
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nEND OF DAY CLOSING LONG POSITION - Price : {self.ltp}')
                            
                            # Print the same message
                            print(f'{self.instrument}\n{self.index}\nEND OF DAY CLOSING LONG POSITION - Price : {self.ltp} \nCapital : {self.capital}')
                            
                            # Print line for readability
                            print('______________________________________________')

                        # If long target 1 has not been achieved
                        else:

                            # We cover all of our open positions and set all flags to False
                            # Set the long position flag to False
                            self.long_position_flag = False

                            # Set the long target 1 flag to False
                            self.long_target_1_flag = False

                            # Set the long target 2 flag to False
                            self.long_target_2_flag = False

                            # Set the short position flag to False
                            self.short_position_flag = False

                            # Set the short target 1 flag to False
                            self.short_target_1_flag = False

                            # Set the short target 2 flag to False
                            self.short_target_2_flag = False
                            
                            # We increase our capital by an amount equal to (the price bought at) * (quantity bought)
                            self.capital = self.capital + (self.position_size * self.ltp)
                            
                            # Send a telegram message specifying the instrument symbol, datetime stamp of order, 
                            # the price filled at and the price set by your strategy's formula
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nEND OF DAY CLOSING LONG POSITION - Price : {self.ltp}')
                            
                            # Print the same message
                            print(f'{self.instrument}\n{self.index}\nEND OF DAY CLOSING LONG POSITION - Price : {self.ltp} \nCapital : {self.capital}')
                            
                            # Print line for readability
                            print('______________________________________________')


                    # If we are long
                    if self.short_position_flag:

                        # If first target has been achieved
                        if self.short_target_1_flag:

                            # We cover the other half of our open positions and set all flags to False
                            # Set the long position flag to False
                            self.long_position_flag = False

                            # Set the long target 1 flag to False
                            self.long_target_1_flag = False

                            # Set the long target 2 flag to False
                            self.long_target_2_flag = False

                            # Set the short position flag to False
                            self.short_position_flag = False

                            # Set the short target 1 flag to False
                            self.short_target_1_flag = False

                            # Set the short target 2 flag to False
                            self.short_target_2_flag = False
                            
                            # We reduce our capital by an amount equal to (the price bought at) * (quantity bought/2)
                            # Because we cover the other half of our position size at stop loss post target 1 being achieved
                            self.capital = self.capital - (self.position_size/2 * self.ltp)
                            
                            # Send a telegram message specifying the instrument symbol, datetime stamp of order, 
                            # the price filled at and the price set by your strategy's formula
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nEND OF DAY CLOSING SHORT POSITION- Price : {self.ltp}')
                            
                            # Print the same message
                            print(f'{self.instrument}\n{self.index}\nEND OF DAY CLOSING SHORT POSITION - Price : {self.ltp} \nCapital : {self.capital}')
                            
                            # Print line for readability
                            print('______________________________________________')

                        # If first target has not been achieved
                        else:

                            # We cover all of our open positions and set all flags to False
                            # Set the long position flag to False
                            self.long_position_flag = False

                            # Set the long target 1 flag to False
                            self.long_target_1_flag = False

                            # Set the long target 2 flag to False
                            self.long_target_2_flag = False

                            # Set the short position flag to False
                            self.short_position_flag = False

                            # Set the short target 1 flag to False
                            self.short_target_1_flag = False

                            # Set the short target 2 flag to False
                            self.short_target_2_flag = False
                            
                            # We reduce our capital by an amount equal to (the price bought at) * (quantity bought)
                            self.capital = self.capital - (self.position_size * ltp)
                            
                            # Send a telegram message specifying the instrument symbol, datetime stamp of order, 
                            # the price filled at and the price set by your strategy's formula
                            telegram_bot.send(f'{self.instrument}\n{self.index}\nEND OF DAY CLOSING SHORT POSITION- Price : {self.ltp}')
                            
                            # Print the same message
                            print(f'{self.instrument}\n{self.index}\nEND OF DAY CLOSING SHORT POSITION - Price : {self.ltp} \nCapital : {self.capital}')
                            
                            # Print line for readability
                            print('______________________________________________')
                            
            # If the time has past the market close hours
            elif ((self.index.date() == self.today) & (self.index.time() > self.market_close)):
                
                # We terminate the thread by setting the flag to check thread run to False
                self.signals_run_thread_flag = False
        
    # -----------------------------------------------------------
    # Start threading to run strategy in the background
    # -----------------------------------------------------------
    
    def send_signals(self):

        # Create new thread for send_signals_for_thread method
        self.thread_send_signals = threading.Thread(target = self.send_signals_for_thread)
        
        # Start running the thread
        self.thread_send_signals.start()
        
    # -----------------------------------------------------------
    # Terminate the strategy thread in the background
    # -----------------------------------------------------------    
        
    def terminate_signals(self):
         
        # Terminate the thread by setting the flag to check thread run to False
        self.signals_run_thread_flag = False