import telepot
import telepot.helper
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from telepot.delegate import (per_chat_id, create_open, pave_event_space, include_callback_query_chat_id)
import time
from datetime import datetime
import requests
import emoji
import json


class BeerBot(telepot.helper.ChatHandler):
    keyboard_1 = InlineKeyboardMarkup(
                        inline_keyboard=[[
                            InlineKeyboardButton(text=emoji.emojize(':sheaf_of_rice: STORAGE'), callback_data='storage'),
                            InlineKeyboardButton(text=emoji.emojize(':hot_springs: MASH'), callback_data='mash')],
                            [InlineKeyboardButton(text=emoji.emojize(':alembic: FERMENTATION'), callback_data='fermentation')]
                        ]
                    )
    keyboard_2 = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text=emoji.emojize(':thermometer: Get measures'), callback_data='get_measures'),
                            InlineKeyboardButton(text=emoji.emojize(':direct_hit: Get current thresholds'), callback_data='get_thresh')],
                            [InlineKeyboardButton(text=emoji.emojize(':level_slider: Set new thresholds'), callback_data='set_thresh'),
                            InlineKeyboardButton(text=emoji.emojize(':BACK_arrow: Back'), callback_data='back_to_dev')]
                        ]
                    )

    def __init__(self, *args, **kwargs):
        super(BeerBot, self).__init__(*args, **kwargs)
        self.set_thresh = False
        self.resources = []
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
                            f"Welcome {name}! This is the IoT Beer bot. Let's start typing your *username*:",
                            parse_mode='Markdown')
            self.step += 1

        elif self.step == 2:
            self.username = msg['text']
            user_info = requests.get(CATALOG_URL + self.username + '/user_information').json()
            if 'ERROR' not in user_info:
                self.password = user_info['password']
                self.sender.sendMessage("Good! Now insert your *password*:", parse_mode='Markdown')
                self.step += 1
            else:
                self.sender.sendMessage("Username not registered in the system. Try again!")

        elif self.step == 3:
            password = msg['text']
            if password == self.password:
                self.sender.sendMessage(
                    f'Access obtained as *{self.username}*!\nNow choose the process you want to control:',
                    parse_mode='Markdown',
                    reply_markup=self.keyboard_1
                )
                self.step += 1
                now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                print(f"[{now}][{self.username}] Access obtained")
            else:
                self.sender.sendMessage("Wrong password. Try again!")

        elif self.set_thresh:
            if self.is_number(msg['text']):
                self.set_thresh = False

                url = CATALOG_URL+self.username+'/services/'+self.selected_process+'/'+self.selected_deviceID+'/update_tsh'
                body = json.dumps({self.selected_resource: round(float(msg['text']), 2)})
                requests.put(url, body)

                sent = self.sender.sendMessage(
                    emoji.emojize(f":ballot_box_with_check: {self.selected_resource} threshold updated!\n\nChoose another option:"),
                    reply_markup=self.keyboard_2
                )
                telepot.helper.Editor(self.bot, sent)

                now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                print(f"[{now}][{self.username}] {self.selected_resource} threshold updated")
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
            self.bot.answerCallbackQuery(query_id, text='Retrieving connected devices...')
            self.connected_devices('storage_control')
        elif query_data == 'mash':
            self.bot.answerCallbackQuery(query_id, text='Retrieving connected devices...')
            self.connected_devices('mash_control')
        elif query_data == 'fermentation':
            self.bot.answerCallbackQuery(query_id, text='Retrieving connected devices...')
            self.connected_devices('fermentation_control')

        elif query_data == 'get_measures':
            self.bot.answerCallbackQuery(query_id, text='Getting measurements...')
            self.get_measures()
        elif query_data == 'get_thresh':
            self.bot.answerCallbackQuery(query_id, text='Getting current thresholds...')
            self.get_thresh()
        elif query_data == 'set_thresh':
            self.bot.answerCallbackQuery(query_id, text='Resources menu')
            self.set_thresh_menu()

        elif query_data == 'back_to_main':
            self.bot.answerCallbackQuery(query_id, text='Back to main menu')
            self.sender.sendMessage(
                    f'Choose the process you want to control:',
                    parse_mode='Markdown',
                    reply_markup=self.keyboard_1
                )
        elif query_data == 'back_to_dev':
            self.bot.answerCallbackQuery(query_id, text='Back to connected devices menu')
            self.connected_devices(self.selected_process)

        elif query_data in self.resources:
            self.selected_resource = query_data
            self.bot.answerCallbackQuery(query_id, text=f'Set new threshold for {self.selected_resource}')
            self.sender.sendMessage(
                    f"*{self.selected_deviceID}* - Insert the new threshold for {self.selected_resource}:",
                    parse_mode='Markdown',
                )
            self.set_thresh = True

        else:
            self.selected_deviceID = query_data
            self.bot.answerCallbackQuery(query_id, text=f'Selected device: {self.selected_deviceID}')
            self.sender.sendMessage(
                    f"*{self.selected_deviceID}* - Choose an option:",
                    parse_mode='Markdown',
                    reply_markup=self.keyboard_2
                )
    
    def connected_devices(self, process):
        self.selected_process = process
        conn_dev = requests.get(CATALOG_URL + self.username + '/devices').json()['device']
        self.process_conn_dev = [dev for dev in conn_dev if dev['location'] == process]
        if self.process_conn_dev:
            self.sender.sendMessage(
                        f'*{process.split("_")[0].upper()}* - Connected devices:',
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard= [
                                list(map(lambda d: InlineKeyboardButton(text=d['deviceID'], callback_data=d['deviceID']), self.process_conn_dev)),
                                [InlineKeyboardButton(text=emoji.emojize(':BACK_arrow: Back'), callback_data='back_to_main')]
                            ]
                        )
                    )
        else:
            self.sender.sendMessage(
                    f'No device connected for *{process.split("_")[0].upper()}*!\nPlease choose a different process:',
                    parse_mode='Markdown',
                    reply_markup=self.keyboard_1
                )

    def get_measures(self):
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        print(f'[{now}][{self.username}] Getting measures for device {self.selected_deviceID}')

        self.selected_device = next((dev for dev in self.process_conn_dev if dev['deviceID'] == self.selected_deviceID))
        end_point = self.selected_device['end_point'] 
        resources = self.selected_device['resources'] 

        icons = {'Temperature':':thermometer:', 'Humidity':':droplet:'}
        meas_units = {'Temperature':'°C', 'Humidity':'%'}
        message = ''
        for resource in resources:
            measure = requests.get(end_point + '/get_measure/' + resource).json()[resource]
            try:
                icon = icons[resource]
                unit = meas_units[resource]
            except:
                icon = ''
                unit = ''
            message += f'{icon} *{resource}*: {measure}{unit}\n'
            
        self.sender.sendMessage(
                emoji.emojize(f'*{self.selected_deviceID}* - Current measures:\n\n' + message),
                parse_mode='Markdown',
                reply_markup=self.keyboard_2
            )

    def get_thresh(self):
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        print(f'[{now}][{self.username}] Getting current thresholds for device {self.selected_deviceID}')

        services = requests.get(CATALOG_URL + self.username + '/services/' + self.selected_process).json()[self.selected_process]
        thresholds = next((dev for dev in services if dev['deviceID'] == self.selected_deviceID))['thresholds']

        # Potrebbero essere messe nel dev_conn_settings
        icons = {'Temperature':':thermometer:', 'Humidity':':droplet:'}
        meas_units = {'Temperature':'°C', 'Humidity':'%'}
        message = ''
        for resource, thresh in thresholds.items():
            try:
                icon = icons[resource]
                unit = meas_units[resource]
            except:
                icon = ''
                unit = ''
            message += f'{icon} *{resource}*: {thresh}{unit}\n'
            
        self.sender.sendMessage(
                emoji.emojize(f'*{self.selected_deviceID}* - Current thresholds:\n\n' + message),
                parse_mode='Markdown',
                reply_markup=self.keyboard_2
            )

    def set_thresh_menu(self):
        self.selected_device = next((dev for dev in self.process_conn_dev if dev['deviceID'] == self.selected_deviceID))
        self.resources = self.selected_device['resources'] 
        self.sender.sendMessage(
                        f'*{self.selected_deviceID}* - Select the resource you want to change the threshold of:',
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard= [
                                list(map(lambda r: InlineKeyboardButton(text=r, callback_data=r), self.resources))
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


CATALOG_URL = 'http://localhost:8080/BREWcatalog/'
TOKEN = '962941325:AAEmgdul_4urnryImw4Rhiz3nsEAG3lz068'

bot = telepot.DelegatorBot(TOKEN, [
    include_callback_query_chat_id(
        pave_event_space())(
            per_chat_id(types=['private']), create_open, BeerBot, timeout=1000),
])
MessageLoop(bot).run_as_thread()

now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
print(f"[{now}] Telegram Bot Started...")	

while 1:
    time.sleep(10)
