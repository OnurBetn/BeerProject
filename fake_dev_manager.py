from MyMQTT import MyMQTT
import json
import time

class DeviceManager_mqtt(object):
    def __init__(self,broker,port):
        self.broker = broker
        self.port = port
        self.clientID = 'dev_manager'
        self.dev_man = MyMQTT(self.clientID, self.broker, self.port, self)
        self.flag = 0
        self.new_msg = {}
        return

    def notify(self,topic,payload):
        self.msg_dict = json.loads(payload)
        print(f'{topic}: {self.msg_dict}')
        return

    def run(self):
        self.dev_man.start()
        return

    def end(self):
        self.dev_man.stop()
        return

    def subscribe(self,topic):
        self.topic = topic
        self.dev_man.mySubscribe(self.topic)
        return

    def publish(self,topic):
        self.topic = topic
        self.action = input('inserisci comando: ')
        self.msg_dict = {'device_action':self.action}
        self.msg = json.dumps(self.msg_dict)
        self.dev_man.myPublish(self.topic, self.msg)

if __name__ == '__main__':
    device_manager = DeviceManager_mqtt('192.168.43.209',1883)
    device_manager.run()
    device_manager.subscribe("nicoL97/storage/dht11-a/Temperature")
    device_manager.subscribe("nicoL97/storage/dht11-a/Humidity")
    topic = 'nicoL97/dht11-a/dev_manager'
    while True:
        device_manager.publish(topic)
        time.sleep(2)
        pass
