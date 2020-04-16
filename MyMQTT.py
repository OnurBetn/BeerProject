import paho.mqtt.client as PahoMQTT

class MyMQTT:

    def __init__ (self,client_id,broker,port,notifier):
        self.broker = broker
        self.port = port
        self.notifier = notifier

        self.clientID = client_id
        self.flag=0

        self._topic= []
        self._isSubscriber = False

        self._paho_mqtt = PahoMQTT.Client(client_id, False)

        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived

    def myOnConnect (self, paho_mqtt, userdata, flags, rc):
        print('\nConnected to %s with result code: %d' %(self.broker, rc))

    def myOnMessageReceived (self, paho_mqtt, userdata, msg):
        #print("\nTopic:'" + msg.topic + "', QoS: '" + str(msg.qos) + "' Message: '" + str(msg.payload) + "'")
        self.notifier.notify(msg.topic,msg.payload)


    def myPublish(self, topic, msg, retain=False):
        print("publishing '%s' with topic '%s'" %(msg,topic))
        self._paho_mqtt.publish(topic,msg,2,retain)

    def mySubscribe(self, topic):
        print("subscribing to %s" %(topic))
        self._paho_mqtt.subscribe(topic,2)
        self._isSubscriber =True
        self._topic.append(topic)

    def start(self):
        self._paho_mqtt.connect(self.broker, self.port)
        self._paho_mqtt.loop_start()

    def stop(self):
        if self._isSubscriber == True:
            for self.topic in self._topic:
                self._paho_mqtt.unsubscribe(self.topic)
                pass
            pass

        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()
