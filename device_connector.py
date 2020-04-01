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
        self.msg_dict = json.loads(msg)
        if 'device_action' in self.msg_dict:
            if 'resource'in self.msg_dict:
                if self.msg_dict['resource'] == self.resource:
                    print(f'message_arrived: {self.msg_dict}')
                    if self.msg_dict['device_action'] == 'RUN':
                        self.stop_flag = 0
                        pass
                    elif self.msg_dict['device_action'] == 'STOP':
                        self.stop_flag = 1
                        pass
                    elif self.msg_dict['device_action'] == 'DISCONNECT':
                        self.stop_flag = 2
                        pass
                    pass
                pass
            pass
        elif 'ALERT' in self.msg_dict:
            self.alert_dict = self.msg_dict['ALERT']
            if 'resource' in self.alert_dict and 'alert_status' in self.alert_dict:
                if self.resource == self.alert_dict['resource']:
                    self.led_status = self.alert_dict['alert_status']
                    if 'alert_type' in self.alert_dict:
                        self.alert_type = self.alert_dict['alert_type']
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
        return
    def run(self):
        self.put_url = self.catalog_uri+'/'+self.device_info['user_owner']+'/add_new_device'
        while True:
            if flag_connection == 0:
                time.sleep(1)
                self.timestamp = time.time()
                self.new_dev1 = self.device_info
                self.new_dev1['insert-timestamp'] = self.timestamp
                try:
                    requests.put(self.put_url, data=json.dumps(self.new_dev1))
                except:
                    break
                time.sleep(59)
                pass
            else:
                break
            pass

        return

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
                            values[res] = thr.RPisensoring(res,thr.pin_sense)
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

class ResourceSenderThread(threading.Thread):
    def __init__(self, resource):
        threading.Thread.__init__(self)
        self.resource = resource
        self.device_pins = settings_dict['device_pins'][self.resource]
        self.pins_out_dict = self.device_pins['output']
        self.pin_sense = self.device_pins['sense']
        self.time_step = settings_dict['time_steps'][self.resource]
        self.unit = settings_dict['units'][self.resource]
        self.current_time = time.time()
        self.mqtt_client = FirstClient(settings_dict['deviceID'], broker['addr'], broker['port'], self.resource)
        self.senML = {"bn": settings_dict['deviceID'], "e": []}
        #for self.type in self.pins_out_dict:
            #GPIO.setup(self.pins_out_dict[self.type], GPIO.OUT)
            #GPIO.output(self.pins_out_dict[self.type], GPIO.LOW)
            #pass

        self.temperature = 18
        return

    def run(self):
        self.mqtt_client.run()
        self.mqtt_client.subscribe(topics_dict['manager'])
        self.timer = self.current_time
        while True:

            if self.mqtt_client.stop_flag == 0 and connector_thread.is_alive() == 1:
                self.event = []
                current_time = time.time()
                if time.time() >= self.timer + self.time_step:
                    self.measure = self.RPisensoring(self.resource, self.pin_sense)
                    if self.measure is not None:
                        self.timer = current_time
                        self.event.append({"n": self.resource, "u": self.unit, "t": self.timer, "v": self.measure})
                    pass

                if self.event:
                    self.senML['e'] = self.event
                    self.mqtt_client.publish(topics_dict['event_notify'], json.dumps(self.senML))
                    pass

                if self.mqtt_client.led_notification:

                    self.led_status = self.mqtt_client.led_status
                    self.alert_type = self.mqtt_client.alert_type
                    if self.led_status == 1:
                        #GPIO.output(self.pins_out_dict[self.alert_type], GPIO.HIGH)
                        print(f'{self.resource} {self.alert_type} actuator = {self.led_status}')
                        pass
                    else:
                        #for self._type in self.pins_out_dict:
                            #if self.pins_out_dict[self._type] is not None:
                                #GPIO.output(self.pins_out_dict[self._type], GPIO.LOW)
                                #pass
                            #pass
                        print(f'{self.resource} actuators = {self.led_status}')
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
        return

    def RPisensoring(self,resource,pin_sense):
        self.measure = None
        self.resource = resource
        self.pin_sense = pin_sense
        if self.resource == 'Temperature' or self.resource == 'Humidity':
            # self.humidity, self.temperature = dht.read_retry(dht.DHT11, self.pin_sense)
            self.humidity = 55

            if self.mqtt_client.alert_type == 'UP' and self.mqtt_client.led_status == 1:
                self.temperature = self.temperature - 1
                pass
            else:
                self.temperature = self.temperature + 1
                pass

            if self.resource == 'Humidity':
                self.measure = self.humidity
                pass
            elif self.resource == 'Temperature':
                self.measure = self.temperature
                pass
            pass

        return self.measure




if __name__ == '__main__':
    catalog_addr = 'http://192.168.43.169:8080/BREWcatalog'
    file_settings = open('device_connector_settings.json', 'r')
    settings_text = file_settings.read()
    file_settings.close()

    settings_dict = json.loads(settings_text)
    resources_list = settings_dict['resources']
    topics_dict = settings_dict['topics']
    broker = requests.get(catalog_addr + '/' + settings_dict['user_owner'] + '/broker').json()
    rest_interface_thread = RestInterface()

    rest_interface_thread.start()

    #GPIO.setwarnings(False)
    #GPIO.setmode(GPIO.BCM)
    flag_connection = 0
    resources_threads = {}
    for resource in resources_list:
        thread = ResourceSenderThread(resource)
        thread.start()
        resources_threads[resource] = thread
        pass

    connector_thread = connectionUpdater(catalog_addr, settings_dict)
    connector_thread.start()

    for res in resources_threads:
        resources_threads[res].join()
        pass

    flag_connection = 1

    print('Disconnection')








