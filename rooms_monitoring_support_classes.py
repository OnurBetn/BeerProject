from MyMQTT import MyMQTT
import json


class ServiceMQTT(object):
    def __init__(self, userID, deviceID, broker, port, tsh):
        self.clientID = userID+'/'+deviceID
        self.userID = userID
        self.deviceID = deviceID
        self.broker = broker
        self.port = port
        self.tsh_dict = tsh
        self.service = MyMQTT(self.clientID,self.broker,self.port,self)
        self.analytic_unit = StorageAnalytics(userID,deviceID,broker,port)

        return

    def notify(self,topic,msg):
        self.new_msg = json.loads(msg)
        self.events = self.new_msg['e']
        for self.event in self.events:

            self.analytic_unit.threshold(self.event, self.tsh_dict)

        return

    def run(self):
        self.service.start()
        return

    def end(self):
        self.analytic_unit.alert_publ.end()
        self.service.stop()
        return

    def publish(self,topic,msg):
        self.service.myPublish(topic,msg)
        return

    def subscribe(self, topic):
        self.service.mySubscribe(topic)
        return

    def updateThreshold(self,new_tsh):
        if self.tsh_dict != new_tsh:
            self.tsh_dict = new_tsh
            pass
        return


class AlertPublisher(object):

    def __init__(self,userID, deviceID, broker, port):
        self.userID = userID
        self.deviceID = deviceID
        self.broker = broker
        self.port = port
        self.clientID = self.userID + self.deviceID + '/alert_publisher'
        self.alert_publ = MyMQTT(self.clientID,self.broker,self.port,self)
        self.measures_dict = {}
        return

    def run(self):
        self.alert_publ.start()
        return

    def end(self):
        self.alert_publ.stop()
        return

    def publish(self,resource,alert_status):
        self.msg = json.dumps({'ALERT':{'resource':resource, 'alert_status': alert_status}})
        self.alert_publ.myPublish(self.userID + '/' + self.deviceID + '/dev_manager',self.msg)
        return


class StorageAnalytics(object):

    def __init__(self,userID,deviceID,broker,port):
        self.userID = userID
        self.deviceID = deviceID
        self.broker = broker
        self.port = port
        self.measures_dict = {}
        self.alert_publ = AlertPublisher(self.userID,self.deviceID,self.broker,self.port)
        self.alert_publ.run()
        return

    def threshold(self,event, tsh):
        self.test = ''
        self.event = event
        self.resource = self.event['n']
        self.new_measure = {'v': self.event['v'], 't': self.event['t']}
        if self.resource not in self.measures_dict:
            self.measures_dict[self.resource] = {'unit': self.event['u'], 'alerts_counter': 0, 'message_flag': 0}
            pass
        self.tsh = tsh[self.resource]

        if self.new_measure['v'] > self.tsh:
            self.test = 'OVER'
            pass

        if self.test == 'OVER':
            self.measures_dict[self.resource]['alerts_counter'] += 1
            pass
        else:
            self.measures_dict[self.resource]['alerts_counter'] = 0
            pass

        if self.measures_dict[self.resource]['alerts_counter'] >= 3 and self.measures_dict[self.resource]['message_flag'] == 0:
            self.measures_dict[self.resource]['alerts_counter'] = 2
            self.alert_publ.publish(self.resource, 1)
            self.measures_dict[self.resource]['message_flag'] = 1
            pass
        elif self.measures_dict[self.resource]['alerts_counter'] == 0 and self.measures_dict[self.resource]['message_flag'] == 1:
            self.alert_publ.publish(self.resource, 0)
            self.measures_dict[self.resource]['message_flag'] = 0
            pass

        return
