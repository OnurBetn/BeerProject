import threading
import time
import requests

from rooms_monitoring_support_classes import *


class roomThread (threading.Thread):
    def __init__(self,userID,deviceID,topics_dict,broker,tsh,active_res):
        threading.Thread.__init__(self)
        self.active_res = active_res
        self.topics_dict = topics_dict
        self.broker_dict = broker
        self.userID = userID
        self.deviceID = deviceID
        self.tsh_dict = tsh
        self.room_mqtt = ServiceMQTT(self.userID,self.deviceID,self.broker_dict['addr'],self.broker_dict['port'],self.tsh_dict)
        self.msg_run = {'device_action': 'RUN','resources':self.active_res}
        self.message_flags = {}
        self.kill_flag = 0
        return

    def run(self):
        self.room_mqtt.run()
        self.room_mqtt.subscribe(self.topics_dict['event_notify'])
        self.room_mqtt.publish(self.topics_dict['manager'],json.dumps(self.msg_run))
        while self.kill_flag == 0:
            time.sleep(5)
            pass

        self.room_mqtt.end()

        return

    def updateResource(self,resources_list):
        if resources_list != self.active_res:
            self.active_res = resources_list
            self.msg_run = {'device_action': 'RUN', 'resources': self.active_res}
            self.room_mqtt.publish(self.topics_dict['manager'], json.dumps(self.msg_run))
        return

    def exit(self):
        self.kill_flag = 1
        pass

class roomsManagerThread(threading.Thread):
    def __init__(self, userID, broker_dict, service_type, catalog_address):
        threading.Thread.__init__(self)
        self.catalog_addr = catalog_address
        self.rooms_threads = {}
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
                self.rooms_list = self.response_dict[self.service_type]
                self.change_flag = 0
                for self.room_dict in self.rooms_list:
                    self.device = requests.get(self.device_url + self.room_dict['deviceID']).json()
                    if 'ERROR' not in self.device:
                        if self.room_dict['status'] == 0:
                            self.thread = roomThread(self.userID, self.device['deviceID'],self.device['topics'], self.broker_dict, self.room_dict['thresholds'],self.room_dict['active_resources'])
                            self.thread.start()
                            self.rooms_threads[self.device['deviceID']] = self.thread
                            self.room_dict['status'] = 1
                            self.change_flag = 1
                            pass
                        else:
                            if self.room_dict['deviceID'] in self.rooms_threads:
                                self.rooms_threads[self.room_dict['deviceID']].room_mqtt.updateThreshold(self.room_dict['thresholds'])
                                self.rooms_threads[self.room_dict['deviceID']].updateResource(self.room_dict['active_resources'])
                                pass
                            else:
                                self.thread = roomThread(self.userID, self.device['deviceID'],self.device['topics'], self.broker_dict, self.room_dict['thresholds'],self.room_dict['active_resources'])
                                self.thread.start()
                                self.rooms_threads[self.device['deviceID']] = self.thread
                            pass
                        pass
                    else:
                        if self.room_dict['status'] == 0:
                            print(f'{self.room_dict["deviceID"]} not CONNECTED')
                            pass
                        else:
                            if self.room_dict['deviceID'] in self.rooms_threads:
                                self.rooms_threads[self.room_dict['deviceID']].exit()
                                self.rooms_threads.pop(self.room_dict['deviceID'])
                                print(f'{self.room_dict["deviceID"]} DISCONNECTED')
                                pass
                            self.room_dict['status'] = 0
                            self.change_flag = 1
                            pass
                        pass
                    if self.change_flag == 1:
                        requests.put(self.service_url + '/' + self.room_dict['deviceID'], data=json.dumps(self.room_dict))
                        pass
                    pass

                time.sleep(5)
            pass
        return



if __name__ == '__main__':

    monitoring_types_list = ['storage_control','fermentation_control']
    catalog_addr = 'http://192.168.43.169:8080/BREWcatalog'
    user_set_file = open('user_information.json', 'r')
    settings = user_set_file.read()
    user_set_file.close()
    login_dict = json.loads(settings)
    services_threads = {}
    user_ID = login_dict['userID']
    topic = user_ID+'/storage'
    broker_dict = requests.get(catalog_addr +'/'+user_ID+'/broker').json()

    for service_type in monitoring_types_list:
        thread = roomsManagerThread(user_ID,broker_dict,service_type,catalog_addr)
        thread.start()
        services_threads[service_type] = thread
        pass














