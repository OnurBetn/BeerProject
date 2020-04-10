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
from MyMQTT import MyMQTT


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
                            InlineKeyboardButton(text=emoji.emojize(':stopwatch: Set new timings'), callback_data='set_times')],
                            [InlineKeyboardButton(text=emoji.emojize(':BACK_arrow: Back'), callback_data='back_to_dev')]
                        ]
                    )

    def __init__(self, *args, **kwargs):
        super(BeerBot, self).__init__(*args, **kwargs)
        self.alert_started = False
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

        if self.alert_started and msg['text'] != '/alertstop':
            self.sender.sendMessage('Please stop alert to use the bot again!')
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
                broker = requests.get(CATALOG_URL + self.username + '/broker').json()
                self.alert_handler = MyMQTT('Alert_Bot_'+self.username, broker['addr'], broker['port'], self)

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
            if msg['text'].isdecimal() or msg['text'].lower() == "null":
                self.set_thresh = False
                new_tsh = int(msg['text']) if msg['text'].isdecimal() else None
                url = CATALOG_URL + self.username + '/services/' + self.selected_process+'/' + self.selected_deviceID
                url += '/update_tsh' if self.ths_or_times_flag == "thresholds" else '/update_timings'
                self.ths_or_times_list[self.tsh_index] = new_tsh
                body = json.dumps({self.selected_resource: self.ths_or_times_list})
                requests.put(url, body)

                sent = self.sender.sendMessage(
                    emoji.emojize(f":ballot_box_with_check: {self.selected_resource} {self.ths_or_times_flag} updated!\n\nChoose another option:"),
                    reply_markup=self.keyboard_2
                )
                telepot.helper.Editor(self.bot, sent)

                now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                print(f"[{now}][{self.username}][{self.selected_deviceID}] {self.selected_resource} {self.ths_or_times_flag} updated")
            else:
                self.sender.sendMessage("Input should be numeric or equal to 'null'! Try again!")

        elif msg['text'] == '/alertstart':
            self.alert_handler.start()
            self.alert_handler.mySubscribe(self.username + '/+/dev_manager')
            self.alert_started = True
            self.sender.sendMessage("Alert started!")

        elif msg['text'] == '/alertstop':
            if self.alert_started:
                self.alert_handler.stop()
                self.alert_started = False
                self.sender.sendMessage("Alert stopped!")
                self.sender.sendMessage(
                    f'Choose the process you want to control:',
                    parse_mode='Markdown',
                    reply_markup=self.keyboard_1
                )
            else:
                self.sender.sendMessage("Alert already stopped!")

        else:
            self.sender.sendMessage("I don't understand you...")

    def on_callback_query(self, msg):
        """Function to handle the callback queries generated from inline keyboard.
	
		Parameters
		----------
        msg : dict 
            message received
		"""
        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')

        if self.alert_started:
            self.sender.sendMessage('Please stop alert to use the bot again!')
            return

        if query_data == 'storage':
            self.connected_devices('storage_control')
            self.bot.answerCallbackQuery(query_id, text='Connected devices')
        elif query_data == 'mash':
            self.connected_devices('mash_control')
            self.bot.answerCallbackQuery(query_id, text='Connected devices')
        elif query_data == 'fermentation':
            self.connected_devices('fermentation_control')
            self.bot.answerCallbackQuery(query_id, text='Connected devices')

        elif query_data == 'get_measures':
            self.get_measures()
            self.bot.answerCallbackQuery(query_id, text='Measurements received')
        elif query_data == 'get_thresh':
            self.get_thresh()
            self.bot.answerCallbackQuery(query_id, text='Current thresholds received')
        elif query_data == 'set_thresh':
            self.set_thresh_or_times_menu("thresholds")
            self.bot.answerCallbackQuery(query_id, text='Resources menu')
        elif query_data == 'set_times':
            self.set_thresh_or_times_menu("timings")
            self.bot.answerCallbackQuery(query_id, text='Resources menu')

        elif query_data == 'back_to_main':
            self.sender.sendMessage(
                    f'Choose the process you want to control:',
                    parse_mode='Markdown',
                    reply_markup=self.keyboard_1
                )
            self.bot.answerCallbackQuery(query_id, text='Back to main menu')
        elif query_data == 'back_to_dev':
            self.connected_devices(self.selected_process)
            self.bot.answerCallbackQuery(query_id, text='Back to connected devices menu')

        elif query_data in self.resources:
            self.ths_or_times_setting(query_data)
            self.bot.answerCallbackQuery(query_id, text=f'Set new {self.ths_or_times_flag} for {self.selected_resource}')
        elif query_data.isdigit():
            self.tsh_index = int(query_data)
            self.sender.sendMessage(
                        f"*{self.selected_deviceID}* - Insert the new {self.ths_or_times_flag[:-1]} for Step {self.tsh_index + 1} of {self.selected_resource}:",
                        parse_mode='Markdown'
                    )
            self.set_thresh = True
            self.bot.answerCallbackQuery(query_id, text=f'Set new {self.ths_or_times_flag[:-1]} for Step {self.tsh_index + 1}')

        else:
            self.selected_deviceID = query_data
            self.sender.sendMessage(
                    f"*{self.selected_deviceID}* - Choose an option:",
                    parse_mode='Markdown',
                    reply_markup=self.keyboard_2
                )
            self.bot.answerCallbackQuery(query_id, text=f'Selected device: {self.selected_deviceID}')
    
    def connected_devices(self, process):
        self.selected_process = process
        conn_dev = requests.get(CATALOG_URL + self.username + '/devices').json()['device']
        self.process_conn_dev = [dev for dev in conn_dev if dev['location'] == process]
        if self.process_conn_dev:
            keyboard = list(map(lambda d: [InlineKeyboardButton(text=d['deviceID'], callback_data=d['deviceID'])], self.process_conn_dev))
            keyboard.append([InlineKeyboardButton(text=emoji.emojize(':BACK_arrow: Back'), callback_data='back_to_main')])
            self.sender.sendMessage(
                        f'*{process.split("_")[0].upper()}* - Connected devices:',
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard= keyboard
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
        print(f'[{now}][{self.username}][{self.selected_deviceID}] Getting measures')

        self.selected_device = next((dev for dev in self.process_conn_dev if dev['deviceID'] == self.selected_deviceID))
        end_point = self.selected_device['end_point'] 
        resources = self.selected_device['resources'] 

        icons = {'Temperature':':thermometer:', 'Humidity':':droplet:'}
        meas_units = {'Temperature':'°C', 'Humidity':'%'}
        message = ''
        for resource in resources:
            measure = requests.get(end_point + '/get_measure/' + resource).json()[resource]
            icon = icons.get(resource, '')
            unit = meas_units.get(resource, '')
            message += f'{icon} *{resource}*: {measure}{unit}\n'
            
        self.sender.sendMessage(
                emoji.emojize(f'*{self.selected_deviceID}* - Current measures:\n\n' + message),
                parse_mode='Markdown',
                reply_markup=self.keyboard_2
            )

    def get_thresh(self):
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        print(f'[{now}][{self.username}][{self.selected_deviceID}] Getting current thresholds')

        services = requests.get(CATALOG_URL + self.username + '/services/' + self.selected_process).json()[self.selected_process]
        device = next((dev for dev in services if dev['deviceID'] == self.selected_deviceID))
        thresholds = device['thresholds']
        timings = device['timings']

        # Potrebbero essere messe nel dev_conn_settings
        icons = {'Temperature':':thermometer:', 'Humidity':':droplet:'}
        meas_units = {'Temperature':'°C', 'Humidity':'%'}
        message = ''
        for resource in thresholds:
            icon = icons.get(resource, '')
            unit = meas_units.get(resource, '')

            if len(thresholds[resource]) > 1:
                message += f'{icon} *{resource}*:\n'
                for k in range(len(thresholds[resource])):
                    message += f'-Step {k+1}: {thresholds[resource][k]}{unit} for {timings[resource][k]} min\n'
            else:
                if timings[resource][0]:
                    message += f'{icon} *{resource}*: {thresholds[resource][0]}{unit} for {timings[resource][0]} min\n'
                else:
                    message += f'{icon} *{resource}*: {thresholds[resource][0]}{unit}\n'

        self.sender.sendMessage(
                emoji.emojize(f'*{self.selected_deviceID}* - Current thresholds:\n\n' + message),
                parse_mode='Markdown',
                reply_markup=self.keyboard_2
            )

    def set_thresh_or_times_menu(self, ths_or_times):
        self.ths_or_times_flag = ths_or_times
        self.selected_device = next((dev for dev in self.process_conn_dev if dev['deviceID'] == self.selected_deviceID))
        self.resources = self.selected_device['resources'] 
        self.sender.sendMessage(
                        f'*{self.selected_deviceID}* - Select the resource you want to change the {ths_or_times} of:',
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard= [
                                list(map(lambda r: InlineKeyboardButton(text=r, callback_data=r), self.resources))
                            ]
                        )
                    )
                
    def ths_or_times_setting(self, query_data):
        self.selected_resource = query_data
        services = requests.get(CATALOG_URL + self.username + '/services/' + self.selected_process).json()[self.selected_process]
        device = next((dev for dev in services if dev['deviceID'] == self.selected_deviceID))
        self.ths_or_times_list = device[self.ths_or_times_flag][self.selected_resource]
        if len(self.ths_or_times_list) == 1:
            self.tsh_index = 0
            self.sender.sendMessage(
                    f"*{self.selected_deviceID}* - Insert the new {self.ths_or_times_flag[:-1]} for {self.selected_resource}:",
                    parse_mode='Markdown'
                )
            self.set_thresh = True
        else:
            self.sender.sendMessage(
                    f"*{self.selected_deviceID}* - Select the step of {self.selected_resource} you want to modify (current {self.ths_or_times_flag} in brackets):",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard= 
                            list(map(lambda t: 
                                [InlineKeyboardButton(text=f'Step {t[0]+1} ({t[1]})', 
                                callback_data=str(t[0]))], enumerate(self.ths_or_times_list)))
                    )
                )

    def notify(self, topic, msg):
        msg_dict = json.loads(msg)
        deviceID = topic.split('/')[1]
        if 'ALERT' in msg_dict:
            msg_dict = msg_dict['ALERT']
            if msg_dict['alert_status']:
                now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                print(f"[{now}][{self.username}][{deviceID}] {msg_dict['resource']} ALERT received!")
                status = "OVER" if msg_dict['alert_type'] == "UP" else "UNDER"
                self.sender.sendMessage( 
                                emoji.emojize(f":warning: *WARNING - {deviceID}* :warning:\n{msg_dict['resource']} *{status}* the threshold!"),
                                parse_mode='Markdown'
                                )

    def on_close(self, ex):
        print(f"[{now}]Bot Closed")
        self.sender.sendMessage("Session closed. Type /start to start again.")


CATALOG_URL = 'http://localhost:8080/BREWcatalog/'
TOKEN = '962941325:AAEmgdul_4urnryImw4Rhiz3nsEAG3lz068'

bot = telepot.DelegatorBot(TOKEN, [
    include_callback_query_chat_id(
        pave_event_space())(
            per_chat_id(types=['private']), create_open, BeerBot, timeout=3600),
])
MessageLoop(bot).run_as_thread()

now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
print(f"[{now}] Telegram Bot Started...")	

while 1:
    time.sleep(10)
