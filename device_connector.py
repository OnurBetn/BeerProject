#import Adafruit_DHT as dht
#import RPi.GPIO as GPIO
import json
from MyMQTT import MyMQTT
import time
import requests
import threading
import cherrypy

class FirstClient(object):
    def __init__(self,client_id,broker,port,resource):
        self.client = MyMQTT(client_id+'/'+resource,broker,port,self)
        self.stop_flag = 1
        self.resource = resource
        self.led_status = 0
        self.led_notification = False
        self.alert_type = None
        return

    def notify(self,topic,msg):
        msg_dict = json.loads(msg)
        if 'device_action' in msg_dict:
            if 'resource'in msg_dict:
                if msg_dict['resource'] == self.resource:
                    print(f'message_arrived: {msg_dict}')
                    if msg_dict['device_action'] == 'RUN':
                        self.stop_flag = 0
                        pass
                    elif msg_dict['device_action'] == 'STOP':
                        self.stop_flag = 1
                        pass
                    elif msg_dict['device_action'] == 'DISCONNECT':
                        self.stop_flag = 2
                        pass
                    pass
                pass
            pass
        elif 'ALERT' in msg_dict:
            alert_dict = msg_dict['ALERT']
            if 'resource' in alert_dict and 'alert_status' in alert_dict:
                if self.resource == alert_dict['resource']:
                    self.led_status = alert_dict['alert_status']
                    if 'alert_type' in alert_dict:
                        self.alert_type = alert_dict['alert_type']
                        pass
                    self.led_notification = True
            pass
        return

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
        self.put_url = self.catalog_uri + '/' + self.device_info['user_owner'] + '/add_new_device'
        self.empty_flag = 0
        self.flag_connection = 0
        return

    def run(self):
        while True:
            if self.flag_connection == 0:
                time.sleep(1)
                flag = self.update()
                if flag is False:
                    break
                time.sleep(59)
                pass
            else:
                break
            pass
        return

    def update(self):
        resp = True
        threadLock.acquire()
        file = open(setting_name, 'r')
        new_info = file.read()
        file.close()
        threadLock.release()
        self.device_info = json.loads(new_info)

        if self.device_info['resources']:
            self.empty_flag = 0
            pass
        else:
            self.empty_flag = 1
            pass

        timestamp = time.time()
        new_dev1 = self.device_info
        new_dev1['insert-timestamp'] = timestamp
        try:
            requests.put(self.put_url, data=json.dumps(new_dev1))
        except:
            resp = False
        return resp


class DeviceHTTP(object):

    exposed = True

    def __init__(self):
        return

    def GET(self,*uri):
        resp = '{}'
        if len(uri) > 0:
            if uri[0] == 'rest':
                if len(uri) > 1:
                    if uri[1] == 'get_measure':
                        values = {}
                        for res in resources_threads:
                            thr = resources_threads[res]
                            values[res] = thr.RPisensoring(thr.pin_sense)
                            pass

                        resp = {}
                        if len(uri) > 2:
                            for res in values:
                                if uri[2] == res:
                                    resp[uri[2]] = values[res]
                                    pass
                                pass
                            if resp == {}:
                                resp[uri[2]] = False
                                pass
                            pass
                        resp = json.dumps(resp)
                        pass
                    pass
                pass
            pass

        return resp

    def PUT(self,*uri):
        if len(uri) > 0:
            if uri[0] == 'rest':
                if len(uri) > 1:
                    if uri[1] == 'update_settings':
                        data = cherrypy.request.body.read()
                        data_dict = json.loads(data)
                        threadLock.acquire()
                        file_sets = open(setting_name, 'w')
                        file_sets.write(json.dumps(data_dict, indent=4))
                        file_sets.close()
                        threadLock.release()
                        connector_thread.update()
                        for r in list(resources_threads):
                            if resources_threads[r].is_alive() == 1:
                                resources_threads[r].update()
                                pass
                            else:
                                resources_threads.pop(r)
                                pass
                            pass

                        for r in data_dict['resources']:
                            if r not in resources_threads:
                                thr = ResourceSenderThread(r)
                                thr.start()
                                resources_threads[r] = thr
                                pass
                            pass
                        pass
                    pass
                pass
            pass

        return


class RestInterface(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        return

    def run(self):
        conf = {
            '/':{
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tools.sessions.on': True
            }
        }

        cherrypy.tree.mount(DeviceHTTP(), '/', conf)

        cherrypy.config.update({'server.socket_host': '0.0.0.0'})
        cherrypy.config.update({'server.socket_port': 8081})

        cherrypy.engine.start()
        cherrypy.engine.block()
        return

    def exit(self):
        cherrypy.engine.exit()
        return


class ResourceSenderThread(threading.Thread):
    def __init__(self, input_res):
        threading.Thread.__init__(self)
        self.resource = input_res
        self.update()
        self.current_time = time.time()
        self.mqtt_client = FirstClient(settings_dict['deviceID'], broker['addr'], broker['port'], self.resource)
        self.senML = {"bn": settings_dict['deviceID'], "e": []}
        #for self.type in self.pins_out_dict:
            #GPIO.setup(self.pins_out_dict[self.type], GPIO.OUT)
            #GPIO.output(self.pins_out_dict[self.type], GPIO.LOW)
            #pass
        self.temperature = 20
        return

    def run(self):
        print(f"Starting {self.resource} thread")
        self.mqtt_client.run()
        self.mqtt_client.subscribe(topics_dict['manager'])
        timer = self.current_time
        while True:

            if self.mqtt_client.stop_flag == 0 and connector_thread.is_alive() == 1:
                event = []
                current_time = time.time()
                if time.time() >= timer + self.time_step:
                    measure = self.RPisensoring(self.pin_sense)
                    if measure is not None:
                        timer = current_time
                        event.append({"n": self.resource, "u": self.unit, "t": timer, "v": measure})
                    pass

                if event:
                    self.senML['e'] = event
                    self.mqtt_client.publish(topics_dict['event_notify'], json.dumps(self.senML))
                    pass

                if self.mqtt_client.led_notification:

                    led_status = self.mqtt_client.led_status
                    alert_type = self.mqtt_client.alert_type
                    if led_status == 1:
                        #GPIO.output(self.pins_out_dict[alert_type], GPIO.HIGH)
                        print(f'{self.resource} {alert_type} actuator = {led_status}')
                        pass
                    else:
                        for _type in self.pins_out_dict:
                            if self.pins_out_dict[_type] is not None:
                                #GPIO.output(self.pins_out_dict[_type], GPIO.LOW)
                                pass
                            pass
                        print(f'{self.resource} actuators = {led_status}')
                        pass

                    self.mqtt_client.led_notification = False
                    pass
                pass

            elif self.mqtt_client.stop_flag == 2:
                break

            elif connector_thread.is_alive() != 1 and self.mqtt_client.stop_flag != 2:
                break

            time.sleep(0.001)
            pass
        self.mqtt_client.end()
        print(f"Closing {self.resource} thread")
        return

    def RPisensoring(self,pin_sense):
        measure = None

        if self.resource == 'Temperature' or self.resource == 'Humidity' or self.resource == 'FluidTemp':
            #humidity, temperature = dht.read_retry(dht.DHT11, pin_sense)
            humidity = 55
            temperature = self.temperature

            if self.mqtt_client.alert_type == 'UP' and self.mqtt_client.led_status == 1:
                temperature = temperature - 1
                pass
            else:
                temperature = temperature + 1
                pass

            if self.resource == 'Humidity':
                measure = humidity
                pass
            elif self.resource == 'Temperature' or self.resource == 'FluidTemp':
                measure = temperature
                pass

            self.temperature = temperature
            pass

        return measure

    def update(self):
        threadLock.acquire()
        file = open(setting_name, 'r')
        new_info = file.read()
        file.close()
        threadLock.release()
        device_info = json.loads(new_info)
        if self.resource in device_info['resources']:
            self.device_pins = device_info['device_pins'][self.resource]
            self.pins_out_dict = self.device_pins['output']
            self.pin_sense = self.device_pins['sense']
            self.time_step = device_info['time_steps'][self.resource]
            self.unit = device_info['units'][self.resource]
            pass
        else:
            self.mqtt_client.stop_flag = 2
            pass

        return


if __name__ == '__main__':
    catalog_addr = 'http://192.168.43.169:8080/BREWcatalog'
    setting_name = 'device_connector_settings.json'

    threadLock = threading.Lock()
    threadLock.acquire()
    file_settings = open(setting_name, 'r')
    settings_text = file_settings.read()
    file_settings.close()
    threadLock.release()

    settings_dict = json.loads(settings_text)
    resources_list = settings_dict['resources']

    if resources_list:
        flag_empty = 0
        pass
    else:
        flag_empty = 1
        pass

    topics_dict = settings_dict['topics']
    broker = requests.get(catalog_addr + '/' + settings_dict['user_owner'] + '/broker').json()
    rest_interface_thread = RestInterface()
    rest_interface_thread.start()

    connector_thread = connectionUpdater(catalog_addr, settings_dict)
    connector_thread.start()

    #GPIO.setwarnings(False)
    #GPIO.setmode(GPIO.BCM)

    resources_threads = {}
    for resource in resources_list:
        thread = ResourceSenderThread(resource)
        thread.start()
        resources_threads[resource] = thread
        pass

    connector_thread.join()

    for res in resources_threads:
        resources_threads[res].join()
        pass

    print('Disconnection')








