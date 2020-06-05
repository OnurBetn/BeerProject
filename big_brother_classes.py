from MyMQTT import MyMQTTconnectionTest
import json
import time
import requests


class TestClient:
    def __init__(self, clientID, broker, port):
        self.clientID = clientID
        self.broker = broker
        self.port = port
        self.service = MyMQTTconnectionTest(self.clientID,self.broker,self.port,self)
        self.notification_flag = 0
        self.rc = None
        self.new_connect = None
        return

    def notify(self,topic,msg):
        self.new_connect = json.loads(msg)
        self.rc = self.new_connect['rc']
        self.notification_flag = 1
        return

    def run(self):
        self.service.start()
        return

    def end(self):
        self.service.stop()
        return


class SetBroker:

    def __init__(self):
        self.client_id = 'broker_test_client'
        self.test_client = None
        self.resp=None
        return

    def verify(self,broker,port):
        self.test_client = TestClient(self.client_id,broker,port)
        self.resp = 10
        try:
            self.test_client.run()
            while self.test_client.notification_flag == 0:
                time.sleep(2)
                pass
            self.resp = self.test_client.rc
            self.test_client.end()
        except TimeoutError:
            print("The host does not respond")
        except:
            print("Address or port invalid!")
        return self.resp


class EditDeviceTools:
    def __init__(self):
        self.resp = None
        self.device_pins = {
            'RaspberryPi': {
                'Temperature': {
                    "sense": 4,
                    "output": {
                        "UP": 17,
                        "DOWN": 27
                    }
                },
                'Humidity': {
                    "sense": 4,
                    "output": {
                        "UP": 23,
                        "DOWN": 24
                    }
                },
                'FluidTemp': {
                    "sense": 25,
                    "output": {
                        "UP": 5,
                        "DOWN": 6
                    }
                }
            }
        }
        self.resources_units = {
            'Temperature': 'Cel',
            'Humidity': '%',
            'FluidTemp': 'Cel'
        }
        self.default_timesteps = {
            "Temperature": 10,
            "Humidity": 10,
            "FluidTemp": 10
        }
        return

    def topics(self,topics_dict,replace,rep_type):
        if rep_type == 'deviceID':
            for topic in topics_dict:
                topic_list = topics_dict[topic].split('/')
                if topic == "event_notify":
                    topic_list[2] = replace
                    pass
                else:
                    topic_list[1] = replace
                    pass
                topics_dict[topic] = '/'.join(topic_list)
                pass
            pass
        elif rep_type == 'location':
            topic_list = topics_dict["event_notify"].split('/')
            topic_list[1] = replace
            topics_dict["event_notify"] = '/'.join(topic_list)
            pass

        self.resp = topics_dict
        return self.resp

    def pins(self,pins_dict,resource,action,device_type):
        if action == 'a':
            try:
                pins_dict[resource] = self.device_pins[device_type][resource]
            except KeyError:
                print("Resource PINS don't exist on device")
                pass
            pass
        elif action == 'd':
            try:
                pins_dict.pop(resource)
            except KeyError:
                print("Resource PINS don't exist on device")
                pass
            pass
        else:
            print("Action ERROR")
            pass
        return pins_dict

    def units(self,units_dict,resource,action):
        if action == 'a':
            try:
                units_dict[resource] = self.resources_units[resource]
            except KeyError:
                print("Resource not recognized")
                pass
            pass
        elif action == 'd':
            try:
                units_dict.pop(resource)
            except KeyError:
                print("Resource not recognized")
                pass
            pass
        else:
            print("Action ERROR")
            pass
        return units_dict

    def timesteps(self,timesteps_dict,resource,action):

        if action == 'a':
            try:
                timesteps_dict[resource] = self.default_timesteps[resource]
            except KeyError:
                print("Resource not recognized")
                pass
            pass
        elif action == 'd':
            try:
                timesteps_dict.pop(resource)
            except KeyError:
                print("Resource not recognized")
                pass
            pass
        else:
            print("Action ERROR")
            pass
        return timesteps_dict















