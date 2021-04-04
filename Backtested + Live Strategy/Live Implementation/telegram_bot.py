import pandas as pd
import telegram

'''

pd.DataFrame({'my_token' : ['1281869431:AAFqr_RZ9BeOn5TC-ON72ztPxYSZPnI8PPg'],
              'chat_id' : [1085701679]
             }).to_csv('telegram_bot_credentials.csv', index=False)
             
'''

telebot_credentials = pd.read_csv('telegram_bot_credentials.csv').iloc[0]

my_chat_id = int(telebot_credentials['chat_id'])
my_token = telebot_credentials['my_token']

def send(msg, chat_id = my_chat_id, token = my_token):
    
    bot = telegram.Bot(token = token)
    bot.sendMessage(chat_id = chat_id, text = msg)