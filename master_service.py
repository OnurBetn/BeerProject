import requests
from service_analysis import *

class ResourceThread(threading.Thread):
    def __init__(self, userID, topics_dict, broker, unit_dict, resource):
        threading.Thread.__init__(self)
        self.resource = resource
        self.tsh_list = unit_dict['thresholds'][self.resource]
        self.topics_dict = topics_dict
        self.broker_dict = broker
        self.userID = userID
        self.deviceID = unit_dict['deviceID']
        self.clientID = self.userID + '/' + self.deviceID + '/' + self.resource
        self.timings_list = unit_dict['timings'][self.resource]
        self.incert_range = unit_dict['incert_ranges'][self.resource]
        self.trend_flag = unit_dict['trend_flag']
        self.unit_mqtt = ServiceMQTT(self.clientID, self.broker_dict['addr'], self.broker_dict['port'], self.resource)
        self.msg_run = {'device_action': 'RUN', 'resource': self.resource}
        self.msg_stop = {'device_action': 'STOP', 'resource': self.resource}
        self.msg_disc = {'device_action': 'DISCONNECT', 'resource': self.resource}
        self.message_flag = 0
        self.kill_flag = 0
        self.sleep_flag = 0
        if self.timings_list[0] is None:
            self.start_time = None
            pass
        else:
            self.start_time = 0
            pass
        self.new_event = {}
        self.analytic_unit = TshAnalytics(self.userID, self.deviceID, self.broker_dict['addr'], self.broker_dict['port'],
                                       self.resource)
        if self.trend_flag == 1:
            self.measures_trend = TrendThread(self.clientID, self.deviceID, self.broker_dict, topics_dict['analytics'],
                                              self.resource)
            pass

        return

    def run(self):
        print('running ' + self.clientID + ' thread')
        self.unit_mqtt.run()
        if self.trend_flag == 1:
            self.measures_trend.start()
            pass
        self.unit_mqtt.subscribe(self.topics_dict['event_notify'])
        time.sleep(2)
        self.unit_mqtt.publish(self.topics_dict['manager'], json.dumps(self.msg_run))
        self.i = 0

        while self.kill_flag == 0:
            if self.sleep_flag == 0:
                if self.unit_mqtt.flag_notify == 1:
                    self.new_event = self.unit_mqtt.event
                    self.unit_mqtt.flag_notify = 0
                    if self.trend_flag == 1:
                        self.measures_trend.update(self.new_event, self.start_time, self.tsh_list[self.i])
                        pass
                    self.analytic_unit.threshold(self.new_event, self.tsh_list[self.i], self.incert_range)
                    if self.start_time == 0:
                        if self.new_event['v'] >= self.tsh_list[self.i]:
                            self.start_time = time.time()
                            pass
                        pass
                    if self.start_time != 0:
                        if self.start_time is not None:
                            if self.new_event['t'] > self.start_time + self.timings_list[self.i]:
                                self.i += 1
                                if self.i == len(self.tsh_list):
                                    self.kill_flag = 1
                                    self.unit_mqtt.publish(self.topics_dict['manager'], json.dumps(self.msg_disc))
                                    time.sleep(2)
                                    pass
                                else:
                                    self.start_time = 0
                                pass
                            pass
                        else:
                            if self.timings_list[0] is not None:
                                self.start_time = time.time()
                                pass
                            pass
                        pass
                    pass
                pass
            time.sleep(0.01)
            pass
        print('closing ' + self.clientID + ' thread')
        if self.trend_flag == 1:
            self.measures_trend.exit()
            pass
        self.unit_mqtt.end()
        self.analytic_unit.alert_publ.end()
        return

    def updateTSH_timings(self, new_tsh_list, new_timings):
        self.new_tsh_list = new_tsh_list
        if len(self.tsh_list) == len(self.new_tsh_list) and self.new_tsh_list != self.tsh_list:
            self.tsh_list = self.new_tsh_list
            pass
        self.new_timings = new_timings
        if len(self.timings_list) == len(self.new_timings) and self.new_timings != self.timings_list:
            self.timings_list = self.new_timings
            pass
        return

    def sleepmode(self,status):
        self.sleep_flag = status
        return

    def exit(self):
        self.kill_flag = 1
        pass


class unitsManagerThread(threading.Thread):
    def __init__(self, userID, broker_dict, service_type, catalog_address):
        threading.Thread.__init__(self)
        self.catalog_addr = catalog_address
        self.units_threads = {}
        self.broker_dict = broker_dict
        self.userID = userID
        self.service_type = service_type
        self.change_flag = 0
        self.service_url = self.catalog_addr + '/' + self.userID + '/services/' + self.service_type
        self.device_url = self.catalog_addr + '/' + self.userID + '/specific_device/'
        return

    def run(self):
        while True:
            self.response_dict = requests.get(self.service_url).json()
            if 'ERROR' in self.response_dict:
                break
            else:
                self.units_list = self.response_dict[self.service_type]
                self.change_flag = 0
                for self.unit_dict in self.units_list:
                    if self.unit_dict['status'] != 2:

                        self.device = requests.get(self.device_url + self.unit_dict['deviceID']).json()
                        if 'ERROR' not in self.device:
                            self.change_flag, self.unit_dict = self.createUpdateThreads(self.unit_dict)
                            pass
                        else:
                            if self.unit_dict['status'] == 0:
                                print(f'{self.unit_dict["deviceID"]} not CONNECTED')
                                pass
                            else:
                                if self.unit_dict['deviceID'] in self.units_threads:
                                    for self.resource in self.units_threads[self.unit_dict['deviceID']]:
                                        self.units_threads[self.unit_dict['deviceID']][self.resource].exit()
                                        pass
                                    self.units_threads.pop(self.unit_dict['deviceID'])
                                    print(f'{self.unit_dict["deviceID"]} DISCONNECTED')
                                    pass
                                self.unit_dict['status'] = 0
                                self.change_flag = 1
                                pass
                            pass
                        if self.change_flag == 1:
                            requests.put(self.service_url + '/' + self.unit_dict['deviceID'],
                                         data=json.dumps(self.unit_dict))
                            pass
                        pass
                    pass

                time.sleep(5)
            pass
        return

    def createUpdateThreads(self,unit_dict):
        self.flag = 0
        self.unit_dict = unit_dict
        if self.device['deviceID'] not in self.units_threads:
            self.units_threads[self.device['deviceID']] = {}
            pass

        for self.resource in self.unit_dict['active_resources']:
            if self.resource not in self.units_threads[self.device['deviceID']]:
                self.thread = ResourceThread(self.userID, self.device['topics'], self.broker_dict, self.unit_dict,self.resource)
                self.thread.start()
                self.units_threads[self.device['deviceID']][self.resource] = self.thread
                pass
            else:
                if self.units_threads[self.device['deviceID']][self.resource].is_alive() == 1:
                    self.tsh = self.unit_dict['thresholds'][self.resource]
                    self.tim = self.unit_dict['timings'][self.resource]
                    self.units_threads[self.device['deviceID']][self.resource].updateTSH_timings(self.tsh, self.tim)
                    pass
                pass
            pass

        if self.units_threads[self.device['deviceID']] != {}:
            for self.resource in self.units_threads[self.device['deviceID']]:
                if self.resource not in self.unit_dict['active_resources']:
                    self.units_threads[self.device['deviceID']][self.resource].sleepmode(1)
                    pass
                else:
                    self.units_threads[self.device['deviceID']][self.resource].sleepmode(0)
                    pass
                pass
            pass

        if self.unit_dict['status'] == 0:
            self.unit_dict['status'] = 1
            self.flag = 1
            pass
        return self.flag, self.unit_dict


if __name__ == '__main__':

    catalog_addr = 'http://192.168.43.169:8080/BREWcatalog'
    user_set_file = open('user_information.json', 'r')
    settings = user_set_file.read()
    user_set_file.close()
    login_dict = json.loads(settings)
    services_threads = {}
    user_ID = login_dict['userID']
    broker_dict = requests.get(catalog_addr + '/' + user_ID + '/broker').json()
    monitoring_types_dict = requests.get(catalog_addr + '/' + user_ID + '/services/list').json()
    monitoring_types_list = monitoring_types_dict['services_list']

    if not monitoring_types_list:
        print('No service available')
        pass
    else:
        for service_type in monitoring_types_list:
            thread = unitsManagerThread(user_ID, broker_dict, service_type, catalog_addr)
            thread.start()
            services_threads[service_type] = thread
            pass
