import threading
import time
import requests

from STORAGE_support_classes import *


class warehouseThread (threading.Thread):
    def __init__(self,userID,deviceID,broker_dict,tsh):
        threading.Thread.__init__(self)
        self.broker_dict = broker_dict
        self.userID = userID
        self.deviceID = deviceID
        self.tsh_dict = tsh

        self.storage_mqtt = ServiceMQTT(self.userID,self.deviceID,self.broker_dict['addr'],self.broker_dict['port'],self.tsh_dict)
        self.msg_run = {'device_action': 'RUN'}
        self.message_flags = {}
        self.kill_flag = 0
        return

    def run(self):
        self.storage_mqtt.run()
        self.storage_mqtt.subscribe(self.userID+'/storage/'+self.deviceID)
        self.storage_mqtt.publish(self.userID+'/'+self.deviceID+'/dev_manager',json.dumps(self.msg_run))
        while self.kill_flag == 0:
            time.sleep(5)
            pass

        self.storage_mqtt.end()

        return

    def exit(self):
        self.kill_flag = 1
        pass


if __name__ == '__main__':
    warehouse_threads = {}
    catalog_addr = 'http://192.168.43.169:8080/BREWcatalog'
    user_set_file = open('user_information.json', 'r')
    settings = user_set_file.read()
    user_set_file.close()
    login_dict = json.loads(settings)

    user_ID = login_dict['userID']
    topic = user_ID+'/storage'
    broker_dict = requests.get(catalog_addr +'/'+user_ID+'/broker').json()

    storage_url = catalog_addr+'/'+user_ID+'/services/storage_control'
    device_url = catalog_addr+'/'+user_ID+'/specific_device/'

    change_flag = 0

    while True:
        response_dict = requests.get(storage_url).json()
        if 'ERROR' in response_dict:
            break
        else:
            storage_list = response_dict['storage_control']
            change_flag = 0
            for warehouse_dict in storage_list:
                device = requests.get(device_url + warehouse_dict['deviceID']).json()
                if 'ERROR' not in device:
                    if warehouse_dict['status'] == 0:
                        thread = warehouseThread(user_ID, device['deviceID'], broker_dict, warehouse_dict['thresholds'])
                        thread.start()
                        warehouse_threads[device['deviceID']] = thread
                        warehouse_dict['status'] = 1
                        change_flag = 1
                        pass
                    else:
                        if warehouse_dict['deviceID'] in warehouse_threads:
                            warehouse_threads[warehouse_dict['deviceID']].storage_mqtt.updateThreshold(warehouse_dict['thresholds'])
                            pass
                        else:
                            thread = warehouseThread(user_ID, device['deviceID'], broker_dict,warehouse_dict['thresholds'])
                            thread.start()
                            warehouse_threads[device['deviceID']] = thread
                        pass
                    pass
                else:
                    if warehouse_dict['status'] == 0:
                        print(f'{warehouse_dict["deviceID"]} not CONNECTED')
                        pass
                    else:
                        if warehouse_dict['deviceID'] in warehouse_threads:
                            warehouse_threads[warehouse_dict['deviceID']].exit()
                            warehouse_threads.pop(warehouse_dict['deviceID'])
                            print(f'{warehouse_dict["deviceID"]} DISCONNECTED')
                            pass
                        warehouse_dict['status'] = 0
                        change_flag = 1
                        pass
                    pass
                if change_flag == 1:
                    requests.put(storage_url + '/' + warehouse_dict['deviceID'], data=json.dumps(warehouse_dict))
                    pass
                pass

            time.sleep(5)
        pass
















