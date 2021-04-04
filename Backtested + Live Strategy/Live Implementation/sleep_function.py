import datetime
import time

def sleeper(hour,minute):
    
    time_now = datetime.datetime.now().time()

    t1 = datetime.timedelta(hours=time_now.hour, minutes=time_now.minute, seconds=time_now.second)
    t2 = datetime.timedelta(hours=hour, minutes=minute)

    duration = t2 - t1

    print(f"Going to sleep until {hour}:{minute}")
    time.sleep(duration.seconds)