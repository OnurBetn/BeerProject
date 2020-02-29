import Adafruit_DHT as dht
import RPi.GPIO as GPIO
import json
from MyMQTT import MyMQTT
import time
import requests
import threading

class FirstClient(object):
    def __init__(self,client_id,broker,port):
        self.client = MyMQTT(client_id,broker,port,self)
        self.stop_flag = 1
        return

    def notify(self,topic,msg):
        self.msg_dict = json.loads(msg)
        print(f'message_arrived: {self.msg_dict}')
        for self.key in self.msg_dict:

            if self.key == 'device_action' and self.msg_dict[self.key] == 'RUN':
                self.stop_flag = 0
                pass

            elif self.key == 'device_action' and self.msg_dict[self.key] == 'STOP':
                self.stop_flag = 1
                pass

            elif self.key == 'device_action' and self.msg_dict[self.key] == 'DISCONNECT':
                self.stop_flag = 2
                pass
            pass

    def run(self):
        self.client.start()

    def end(self):
        self.client.stop()

    def subscribe(self, topic):
        self.client.mySubscribe(topic)

    def publish(self, topic, message):
        self.client.myPublish(topic, message)

class connectionUpdater(threading.Thread):
    def __init__(self, catalog, dev_info):
        threading.Thread.__init__(self)
        self.catalog_uri = catalog
        self.device_info = dev_info
        return
    def run(self):
        self.put_url = self.catalog_uri+'/'+self.device_info['user_owner']+'/add_new_device'
        while True:
            if rasp_client.stop_flag != 2:
                self.timestamp = time.time()
                self.new_dev1 = self.device_info
                self.new_dev1['insert-timestamp'] = self.timestamp
                try:
                    self.resp = requests.put(self.put_url, params=self.new_dev1).text
                except:
                    break
                time.sleep(60)
                pass
            else:
                break
            pass

if __name__ == '__main__':
    catalog_addr = 'http://192.168.43.169:8080/BREWcatalog'
    file_settings = open('device_connector_settings.json', 'r')
    settings_text = file_settings.read()
    file_settings.close()
    settings_dict = json.loads(settings_text)
    topics_list = settings_dict['topics']
    resources_list = settings_dict['resources']
    time_steps_list = settings_dict['time_steps']
    broker = requests.get(catalog_addr + '/' + settings_dict['user_owner'] + '/broker').json()
    rasp_client = FirstClient('Raspberry', broker['addr'], broker['port'])
    rasp_client.run()
    rasp_client.subscribe(settings_dict['user_owner'] +'/'+ settings_dict['deviceID'] + '/dev_manager')

    connector_thread = connectionUpdater(catalog_addr,settings_dict)
    connector_thread.start()

    pin_sense=4
    GPIO.setmode(GPIO.BCM)
    time.sleep(2)
    timer_temp = time.time()
    timer_hum = time.time()
# Le seguenti due operazioni servono per simulare il funzionamento su PC: quando si carica il programma su RPi è necessario eliminare le due seguenti righe e togliere dai commenti le operazioni del raspberry
    #humidity= 40
    #temperature = 18

    while time.time():

        if rasp_client.stop_flag == 0 and connector_thread.is_alive() == 1:
            if time.time() >= timer_hum + time_steps_list[1]:
                humidity, temperature = dht.read_retry(dht.DHT11, pin_sense)
                rasp_client.publish(topics_list[1], json.dumps({resources_list[1]: humidity}, indent=4))
                timer_hum = time.time()
                pass
            if time.time() >= timer_temp + time_steps_list[0]:
                humidity, temperature = dht.read_retry(dht.DHT11, pin_sense)
                rasp_client.publish(topics_list[0], json.dumps({resources_list[0]: temperature}, indent=4))
                timer_temp = time.time()
                pass

        elif rasp_client.stop_flag == 2:
            print('Disconnection')
            break

        elif connector_thread.is_alive() != 1 and rasp_client.stop_flag != 2:
            print('Connection ERROR!')
            break
        pass

    rasp_client.end()





