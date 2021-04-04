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
from YourStrategyProject import YourStrategy


# Run only when this file is not imported
if __name__ == '__main__':
    
    
    # Define your input
    # A dictionary with keys being the symbol names and values also being a dictionary with the exchange and quantity specified
    # Example : 
        # input_dictionary = {
        #                    '<instrument 1 symbol name>': {'exchange' : '<instrument 1 exchange>', 
        #                                                   'quantity' : <instrument 1 quantity>},
        
        #                    '<instrument 2 symbol name>': {'exchange' : '<instrument 2 exchange>',  
        #                                                   'quantity' : <instrument 2 quantity>},
        
        #                    '<instrument 3 symbol name>': {'exchange' : '<instrument 3 exchange>',
        #                                                   'quantity' : <instrument 3 quantity>}
        #                    }
        
    input_instruments = {
                    'AXISBANK JUL FUT': {'exchange' : 'NFO', 'quantity' : 2},
                    'BAJFINANCE JUL FUT': {'exchange' : 'NFO', 'quantity' : 2},
                    'ICICIBANK JUL FUT': {'exchange' : 'NFO', 'quantity' : 2},
                    'NIFTY JUL FUT': {'exchange' : 'NFO', 'quantity' : 2},
                    'BANKNIFTY JUL FUT': {'exchange' : 'NFO', 'quantity' : 2}
              }
    
    # Create an instance of the AmadeusData_AliceBlue class and pass 1 minute as timeframe and the input dictionary
    amadeus_data = AmadeusData_AliceBlue('1min', input_instruments)
    
    # Put this system to sleep until 9:25 AM
    sleeper(9, 25)
    
    # Start the live data feed using the AmadeusData_AliceBlue object
    # RUN THIS ONLY ONCE
    amadeus_data.get_live_data_initialise()
    
    # Create an empty dictionary to store instances of YourStrategy class for instruments specified
    # in the input_instruments dictionary
    strategy_implemented = dict()
    
    # Iterate over the instruments in the input_instruments dictionary
    for instrument in input_instruments:
        
        # Add a new item to the strategy_implemented dictionary to save instance of the YourStrategy object created
        strategy_implemented[instrument] = YourStrategy(instrument, input_instruments[instrument]['exchange'], amadeus_data.data[instrument], input_instruments[instrument]['quantity'])
        
        # Start a thread to get signals according the the defined strategy
        strategy_implemented[instrument].send_signals()