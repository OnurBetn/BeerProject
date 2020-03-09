import telepot
import telepot.helper
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from telepot.delegate import (per_chat_id, create_open, pave_event_space, include_callback_query_chat_id)
import time
import requests
import emoji


class BeerBot(telepot.helper.ChatHandler):
    def __init__(self, *args, **kwargs):
        super(BeerBot, self).__init__(*args, **kwargs)
        self.set_temp_storage = False
        self.step = 1

    def on_chat_message(self, msg):
        """Function to handle messages received from users.
	
		Parameters
		----------
        msg : dict 
            message received
		"""
        content_type, chat_type, chat_id = telepot.glance(msg)

        if content_type != 'text':
            self.sender.sendMessage('Message type not supported!')
            return

        if msg['text'] == '/start' or self.step == 1:
            self.step = 1
            name = msg["from"]["first_name"]
            self.sender.sendMessage( 
                            f"Welcome {name}! This is the IoT Beer bot. Let's start typing your *username*",
                            parse_mode='Markdown')
            self.step += 1

        elif self.step == 2:
            self.username = msg['text']
            r = requests.get(URL + '/BREWcatalog/' + self.username + '/user_information')
            if r.status_code == requests.codes.ok:
                self.password = r.json()['password']
                self.sender.sendMessage( 
                                "Good! Now insert your *password*",
                                parse_mode='Markdown')
                self.step += 1
            else:
                self.sender.sendMessage("Username not registered in the system. Try again!")

        elif self.step == 3:
            password = msg['text']
            if password == self.password:
                self.sender.sendMessage(
                    f'Access obtained as *{self.username}*!\nNow choose the process you want to control:',
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[[
                            InlineKeyboardButton(text=emoji.emojize(':sheaf_of_rice: STORAGE'), callback_data='storage'),
                            InlineKeyboardButton(text=emoji.emojize(':hot_springs: MASH'), callback_data='mash')],
                            [InlineKeyboardButton(text=emoji.emojize(':alembic: FERMENTATION'), callback_data='fermentation')]
                        ]
                    )
                )
                print(f"[Telegram Bot][{self.username}] Obtained access.")
            else:
                self.sender.sendMessage("Wrong password. Try again!")

        elif self.set_temp_storage:
            if self.is_number(msg['text']):
                self.set_temp_storage = False

                # TODO: update temp in the catalog

            else:
                self.sender.sendMessage("Input should be numeric! Try again!")

    def on_callback_query(self, msg):
        """Function to handle the callback queries generated from inline keyboard.
	
		Parameters
		----------
        msg : dict 
            message received
		"""
        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')

        if query_data == 'storage':
            self._storage()
        elif query_data == 'mash':
            self.bot.answerCallbackQuery(query_id, text='You pressed MASH')
        elif query_data == 'fermentation':
            self.bot.answerCallbackQuery(query_id, text='You pressed FERMENTATION')

        elif query_data == 'get_temp_storage':
            self.bot.answerCallbackQuery(query_id, text='You pressed FERMENTATION')
        elif query_data == 'set_temp_storage':
            self.set_temp_storage = True
            self.sender.sendMessage("Insert the new desired temperature:")
    
    def _storage(self):
        self.sender.sendMessage(
                    '*Storage room* - Choose an option:',
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text=emoji.emojize(':thermometer: Get Temperature & Humidity'), callback_data='get_temp_storage')],
                            [InlineKeyboardButton(text=emoji.emojize(':direct_hit: Set Target Temperature'), callback_data='set_temp_storage')]
                        ]
                    )
                )
	
    def is_number(self, s):
        try:
            float(s)
            return True
        except ValueError:
            pass
        return False


URL = 'http://localhost:8080'
TOKEN = '962941325:AAEmgdul_4urnryImw4Rhiz3nsEAG3lz068'

bot = telepot.DelegatorBot(TOKEN, [
    include_callback_query_chat_id(
        pave_event_space())(
            per_chat_id(types=['private']), create_open, BeerBot, timeout=1000),
])
MessageLoop(bot).run_as_thread()

print("[Telegram Bot] Started...")	

while 1:
    time.sleep(10)
