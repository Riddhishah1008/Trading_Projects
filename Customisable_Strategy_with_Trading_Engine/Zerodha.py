# -----------------------------------------------------------
# Getting started with Jugaad Trader
# -----------------------------------------------------------


### Code to run on the command line ###

# Commands:
#   configdir     Print app config directory location
#   rm            Delete stored credentials or sessions config To delete...
#   savecreds     Saves your creds in the APP config directory
#   startsession  Saves your login session in the app config folder


# -----------------------------------------------------------
### Start Session ###

# $ jtrader zerodha startsession
# User ID >: USERID
# Password >:
# Pin >:
# Logged in successfully as XYZ
# Saved session successfully
# -----------------------------------------------------------


# -----------------------------------------------------------
### Save Credentials ###

# $ jtrader zerodha savecreds
# Saves your creds in app config folder in file named .zcred
# User ID >: USERID
# Password >:
# Pin >:
# Saved credentials successfully

# Once you have done this, you can call load_creds followed by login.

from jugaad_trader import Zerodha
kite = Zerodha()
kite.load_creds()
kite.login()
print(kite.profile())


# -----------------------------------------------------------


# -----------------------------------------------------------
### Config Directory ###

# $ jtrader zerodha configdir


###### Delete configuration ######

### To delete SESSION ###

# $ jtrader zerodha rm SESSION

### To delete CREDENTIALS ###

# $ jtrader zerodha rm CREDENTIALS

# -----------------------------------------------------------



# -----------------------------------------------------------
# HOW TO GET HISTORICAL DATA
# -----------------------------------------------------------

# Import zerodha class from jugaad trader library
from jugaad_trader import Zerodha

# Create an instance of Zerodha object
kite = Zerodha()

# Load the saved credentials
kite.load_creds()

# Login to Zerodha
kite.login()

# View your profile details
print(kite.profile())

# Get Instrument Token number by specifying instrument symbol
# Here we take GOLDM AUG FUTURES as example
instrument_symbol = 'MCX:GOLDM20AUGFUT'
# Use quote method to extract token number from symbol name
instrument_token = kite.quote(instrument_symbol).get(instrument_symbol).get('instrument_token')

# Dates between which we need historical data
# From Date
from_date = "2020-07-22 09:15:00"
# To Date
to_date = "2020-07-27 09:30:00"

# Interval(minute, day, 3 minute, 5 minute...)
interval = "minute"

# Store the historical data in a dataframe
historical_data = pd.DataFrame(kite.historical_data(instrument_token, from_date, to_date, interval, continuous=False, oi=False))

### Clean the Zerodha historical data to match its format to AliceBlue live data ###
    
# Create datetime column which is equal to the Zerodha historical data's date column
historical_data['datetime'] = historical_data['date']

# Create new column ticker to store symbol name
historical_data['ticker'] = instrument_symbol

# Reassign date column to the date extracted from datetime column
historical_data['date'] = historical_data['datetime'].apply(lambda x : x.date())

# Create time column to the time extracted from datetime column
historical_data['time'] = historical_data['datetime'].apply(lambda x : x.time())

# Reorder column names in the dataframe
historical_data = historical_data[['datetime','ticker','open','high','low','close','volume','date','time']]

# Reassign datetime column as a combined string form of date and time from the respective columns
historical_data['datetime'] = historical_data['date'].apply(str) + historical_data['time'].apply(str)

# Set datetime column to datetime format using strptime method
historical_data['datetime'] = historical_data['datetime'].apply(lambda x : datetime.datetime.strptime(x, '%Y-%m-%d%H:%M:%S'))

# Set datetime column as index
historical_data.set_index('datetime', inplace=True)