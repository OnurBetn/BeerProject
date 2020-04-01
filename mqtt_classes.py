import json
from MyMQTT import MyMQTT


class ServiceMQTT(object):
    def __init__(self, clientID, broker, port, resource):
        self.resource = resource
        self.clientID = clientID
        self.broker = broker
        self.port = port
        self.service = MyMQTT(self.clientID,self.broker,self.port,self)
        self.flag_notify = 0
        return

    def notify(self,topic,msg):
        self.new_msg = json.loads(msg)
        self.events = self.new_msg['e']
        for self.e in self.events:
            if self.e['n'] == self.resource:
                self.event = self.e
                self.flag_notify = 1
                pass
            pass

        return

    def run(self):
        print('starting ' + self.clientID +' mqtt')
        self.service.start()
        return

    def end(self):
        print('closing ' + self.clientID + ' mqtt')
        self.service.stop()
        return

    def publish(self,topic,msg):
        self.service.myPublish(topic,msg)
        return

    def subscribe(self, topic):
        self.service.mySubscribe(topic)
        return


class AlertPublisher(object):

    def __init__(self,userID, deviceID, broker, port, resource):
        self.userID = userID
        self.deviceID = deviceID
        self.broker = broker
        self.port = port
        self.resource = resource
        self.clientID = self.userID +'/'+ self.deviceID +'/'+self.resource+ '/alert_publisher'
        self.alert_publ = MyMQTT(self.clientID,self.broker,self.port,self)
        return

    def run(self):
        print('starting '+self.clientID+' mqtt')
        self.alert_publ.start()
        return

    def end(self):
        print('closing ' + self.clientID+' mqtt')
        self.alert_publ.stop()
        return

    def publish(self,resource,alert_status,alert_type):
        self.msg = json.dumps({'ALERT':{'resource':resource, 'alert_status': alert_status, 'alert_type':alert_type}})
        self.alert_publ.myPublish(self.userID + '/' + self.deviceID + '/dev_manager',self.msg)
        return

