# -----------------------------------------------------------
# Import required libraries
# -----------------------------------------------------------

import datetime
import time

# -----------------------------------------------------------
# Sleeper Function to sleep until the specified time
# -----------------------------------------------------------

def sleeper(hour ,minute=0, second=0):
    
    '''
    Puts the function to sleep until the specfied time
    Inputs : hours, minutes (default 0), seconds (default 0)
    Example : (10) for 10 AM
              (9,8) for 09:08 AM
              (15,30,20) for 3:30:20 PM
    '''
    
    # Store the current time 
    time_now = datetime.datetime.now().time()

    # Create a timedelta object using the current time
    t1 = datetime.timedelta(hours=time_now.hour, minutes=time_now.minute, seconds=time_now.second)
    
    # Create a timedelta object of the time until which you want it to sleep
    t2 = datetime.timedelta(hours=hour, minutes=minute, seconds=second)

    # Calculate the differnce between the current time and the time you want it to sleep until
    duration = t2 - t1

    # Print till what time it would be going to sleep
    print(f"Going to sleep until {hour}:{minute}:{second}")
    
    # Go to sleep for the determined number of seconds
    time.sleep(duration.seconds)