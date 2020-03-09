import Adafruit_DHT as dht
import RPi.GPIO as GPIO
import json
from MyMQTT import MyMQTT
import time
import requests
import threading

class FirstClient(object):
    def __init__(self,client_id,broker,port,resources_list):
        self.client = MyMQTT(client_id,broker,port,self)
        self.stop_flag = 1
        self.resources = resources_list
        self.led_status = {}
        self.led_notification = False
        for self.resource in self.resources:
            self.led_status[self.resource] = 0
            pass
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

            elif self.key == 'ALERT':
                self.alert_dict = self.msg_dict[self.key]
                self.led_status[self.alert_dict['resource']] = self.alert_dict['alert_status']
                self.led_notification = True
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
                    requests.put(self.put_url, data=json.dumps(self.new_dev1))
                except:
                    break
                time.sleep(60)
                pass
            else:
                break
            pass
        return


if __name__ == '__main__':
    catalog_addr = 'http://192.168.43.169:8080/BREWcatalog'
    file_settings = open('device_connector_settings.json', 'r')
    settings_text = file_settings.read()
    file_settings.close()

    settings_dict = json.loads(settings_text)
    senML = {"bn": settings_dict['deviceID'], "e": []}
    resources_list = settings_dict['resources']
    time_steps_list = settings_dict['time_steps']
    units_list = settings_dict['units']
    broker = requests.get(catalog_addr + '/' + settings_dict['user_owner'] + '/broker').json()
    rasp_client = FirstClient('Raspberry', broker['addr'], broker['port'],resources_list)
    rasp_client.run()
    rasp_client.subscribe(settings_dict['user_owner'] +'/'+ settings_dict['deviceID'] + '/dev_manager')

    connector_thread = connectionUpdater(catalog_addr,settings_dict)
    connector_thread.start()

    pin_sense = 4
    pin_dehum = 27
    pin_cooler = 17
    out_pin_dict = {resources_list[0]: pin_cooler, resources_list[1]: pin_dehum}

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    for resource in out_pin_dict:
        GPIO.setup(out_pin_dict[resource], GPIO.OUT)
        pass

    current_time = time.time()
    timer_temp = current_time
    timer_hum = current_time
# Le seguenti due operazioni servono per simulare il funzionamento su PC: quando si carica il programma su RPi è necessario eliminare le due seguenti righe e togliere dai commenti le operazioni del raspberry
    #humidity= 65
    #temperature = 24

    while time.time():

        if rasp_client.stop_flag == 0 and connector_thread.is_alive() == 1:
            event = []
            humidity, temperature = dht.read_retry(dht.DHT11, pin_sense)
            current_time = time.time()
            if time.time() >= timer_hum + time_steps_list[1]:
                timer_hum = current_time
                event.append({"n": resources_list[1], "u": units_list[1], "t": timer_hum, "v": humidity})
                pass

            if time.time() >= timer_temp + time_steps_list[0]:
                timer_temp = current_time
                event.append({"n": resources_list[0], "u": units_list[0], "t": timer_temp, "v":temperature})
                pass
            if event:
                senML['e'] = event
                rasp_client.publish(settings_dict['user_owner']+'/'+settings_dict['location']+'/'+settings_dict['deviceID'], json.dumps(senML))
                pass

            if rasp_client.led_notification:

                led_status = rasp_client.led_status
                for resource in led_status:
                    if led_status[resource] == 1:
                        GPIO.output(out_pin_dict[resource], GPIO.HIGH)
                        print(f'{resource} actuator = 1')
                        pass
                    else:
                        GPIO.output(out_pin_dict[resource], GPIO.LOW)
                        print(f'{resource} actuator = 0')
                        pass
                    pass

                rasp_client.led_notification = False
                pass
            pass

        elif rasp_client.stop_flag == 2:
            print('Disconnection')
            break

        elif connector_thread.is_alive() != 1 and rasp_client.stop_flag != 2:
            print('Connection ERROR!')
            break
        pass

    rasp_client.end()





