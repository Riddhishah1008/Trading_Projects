# -----------------------------------------------------------
# Import required libraries
# -----------------------------------------------------------

import pandas as pd
import telegram

# -----------------------------------------------------------
# Run the following only once with your credentials to save the CSV
# -----------------------------------------------------------

'''

pd.DataFrame({'my_token' : ['<your_token>'],
              'chat_id' : [<your_chat_id>]
             }).to_csv('telegram_bot_credentials.csv', index=False)
             
'''

# Read your credentials from the CSV
telebot_credentials = pd.read_csv('telegram_bot_credentials.csv').iloc[0]

# Retrieve the chat ID from your credentials
my_chat_id = int(telebot_credentials['chat_id'])

# Retrieve the token from your credentials
my_token = telebot_credentials['my_token']

# Send message to your telegram channel, by default to the chat ID and token in the credentials unless specified
def send(msg, chat_id = my_chat_id, token = my_token):
    
    # Create a Telegram Bot instance
    bot = telegram.Bot(token = token)
    
    # Send the message specified in the argument
    bot.sendMessage(chat_id = chat_id, text = msg)