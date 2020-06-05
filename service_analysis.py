from mqtt_classes import *
import numpy
import threading
import time

class TshAnalytics(object):

    def __init__(self,userID,deviceID,broker,port,resource):
        self.userID = userID
        self.deviceID = deviceID
        self.broker = broker
        self.port = port
        self.resource = resource
        self.measures_dict = {}
        self.alert_publ = AlertPublisher(self.userID,self.deviceID,self.broker,self.port,self.resource)
        try:
            self.alert_publ.run()
        except TimeoutError:
            print("The host does not respond")
            pass
        return

    def threshold(self,event, tsh, incert):
        self.test = ''
        self.event = event
        self.resource = self.event['n']
        self.new_measure = {'v': self.event['v'], 't': self.event['t']}
        if self.measures_dict == {}:
            self.measures_dict = {'unit': self.event['u'], 'over_counter': 0,'under_counter': 0, 'message_flag': 0}
            pass
        self.tsh = tsh
        self.incert = incert
        if self.incert is not None:
            if self.new_measure['v'] > self.tsh + self.incert:
                self.test = 'OVER'
                pass
            elif self.new_measure['v'] < self.tsh - self.incert:
                self.test = 'UNDER'
                pass
            pass
        else:
            if self.new_measure['v'] > self.tsh:
                self.test = 'OVER'
                pass
            pass

        if self.test == 'OVER':
            self.measures_dict['over_counter'] += 1
            pass
        elif self.test == 'UNDER':
            self.measures_dict['under_counter'] += 1
        else:
            self.measures_dict['over_counter'] = 0
            self.measures_dict['under_counter'] = 0
            pass

        if self.measures_dict['over_counter'] >= 3:
            self.measures_dict['over_counter'] = 1
            self.alert_publ.publish(self.resource, 1, 'UP')
            self.measures_dict['message_flag'] = 1
            pass
        elif self.measures_dict['under_counter'] >= 3:
            self.measures_dict['under_counter'] = 1
            self.alert_publ.publish(self.resource, 1, 'DOWN')
            self.measures_dict['message_flag'] = 1
            pass
        elif self.measures_dict['over_counter'] == 0 and self.measures_dict['under_counter'] == 0 and self.measures_dict['message_flag'] == 1:
            self.alert_publ.publish(self.resource, 0, None)
            self.measures_dict['message_flag'] = 0
            pass

        return

class TrendThread(threading.Thread):
    def __init__(self,clientID,deviceID,broker,topic, resource):
        threading.Thread.__init__(self)
        self.senML = {"bn": deviceID, "e": []}
        self.resource = resource
        self.clientID = clientID
        self.broker_dict = broker
        self.topic = topic
        self.last_five = {"x":[],"y":[]}
        self.trend_mqtt = ServiceMQTT(self.clientID+'/trend_agent',self.broker_dict['addr'],self.broker_dict['port'],self.resource)
        self.start_timestamp = 0
        self.resource = ''
        self.unit = ''
        self.kill_flag = 0
        self.new_update = 0
        self.flag_time_estimation = 0
        self.new_measure = {}
        self.current_tsh = 0
        self.val_trend = None
        return

    def run(self):
        print(f'starting {self.clientID}/trend_agent')
        self.trend_mqtt.run()
        while self.kill_flag == 0:
            self.event = []
            if self.new_update == 1:
                self.new_update = 0
                self.message = self.trend()
                if self.message is not None:
                    self.event.append(self.message)
                    pass
                if self.flag_time_estimation == 0:
                    self.message = self.time_to_tsh(self.current_tsh)
                    if self.message is not None:
                        self.event.append(self.message)
                    pass
                if self.event:
                    self.senML['e'] = self.event
                    self.trend_mqtt.publish(self.topic, json.dumps(self.senML))
                pass
            time.sleep(0.01)
            pass
        self.trend_mqtt.end()
        print(f'closing {self.clientID}/trend_agent')

    def update(self,new_measure, flag_time_estimation, current_tsh):
        self.new_measure = new_measure
        self.flag_time_estimation = flag_time_estimation
        self.current_tsh = current_tsh
        self.new_update = 1
        return

    def trend(self):
        self.msg = None
        if len(self.last_five["x"]) == 0:
            self.start_timestamp = self.new_measure['t']
            self.resource = self.new_measure['n']
            self.unit = self.new_measure['u']

        if len(self.last_five["x"]) == 5:
            self.last_five["x"].pop(0)
            self.last_five["y"].pop(0)
            self.last_five["x"].append(self.new_measure["t"]-self.start_timestamp)
            self.last_five["y"].append(self.new_measure["v"])
            pass
        else:
            self.last_five["x"].append(self.new_measure["t"]-self.start_timestamp)
            self.last_five["y"].append(self.new_measure["v"])
            pass

        if len(self.last_five["x"]) >= 2:
            self.p = numpy.polyfit(self.last_five["x"],self.last_five["y"], 1)
            self.val_trend = round(float(self.p[0]),3)
            self.msg = {"n":self.resource+"/trend","u": self.unit+"/s","t":self.new_measure["t"],"v":self.val_trend}

            pass

        else:
            self.val_trend = None

        return self.msg

    def time_to_tsh(self,tsh):
        self.msg = None
        if self.val_trend != 0 and self.val_trend is not None:
            self.time_eval = (tsh - self.new_measure['v']) / self.val_trend
            self.time_eval = round(self.time_eval)
            pass
        else:
            self.time_eval = None
            pass
        self.msg = {"n":self.resource+"/time_to_tsh","u": "s","t":self.new_measure["t"],"v":self.time_eval}
        return self.msg

    def exit(self):
        self.kill_flag = 1
        return
