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
from AliceBlueData import AmadeusData_AliceBlue
from GamePlanStrategy import GamePlan
from sleep_function import sleeper
from collections import namedtuple
from collections import defaultdict
from jugaad_trader import Zerodha

if __name__ == '__main__':
    
    ins_exc = {
                    'AXISBANK JUL FUT': {'exchange' : 'NFO', 'quantity' : 2},
                    'BAJFINANCE JUL FUT': {'exchange' : 'NFO', 'quantity' : 2},
                    'ICICIBANK JUL FUT': {'exchange' : 'NFO', 'quantity' : 2},
                    'NIFTY JUL FUT': {'exchange' : 'NFO', 'quantity' : 2},
                    'BANKNIFTY JUL FUT': {'exchange' : 'NFO', 'quantity' : 2}
              }
    
    #ins_exc = {
    #                'GOLDM AUG FUT': {'exchange' : 'MCX', 'quantity' : 2},
    #          }
    
    try:
        amadeus_data = AmadeusData('1min', ins_exc)

    except Exception as e:
        telegram_bot.send(f'Error has occured while creating Amadeus Data Client object \n{e}')
        print(f'Error has occured while creating Amadeus Data Client objectd \n{e}')
        exit()
    
    time.sleep(9,25)

    try:
        amadeus_data.get_live_data()

    except Exception as e:
        telegram_bot.send(f'Error has occured while trying to get Live Data Feed \n{e}')
        print(f'Error has occured while trying to get Live Data Feed \n{e}')
        exit()
    
    game_plan = {}
    
    for instrument in ins_exc:
        
        game_plan[instrument] = GamePlan(instrument, ins_exc[instrument]['exchange'], amadeus_data.data[instrument], ins_exc[instrument]['quantity'])
        game_plan[instrument].send_signals()