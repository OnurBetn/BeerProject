import threading
import time
import cherrypy
from CATALOG_support_classes import *


class CatalogManager(object):

    exposed = True

    def __init__(self):
        return

    def GET(self,*uri):
        resp = ''
        threadLock.acquire()
        file_catalog = open("catalog.json", "r")
        catalog_json = file_catalog.read()
        file_catalog.close()
        threadLock.release()
        catalog_dict = json.loads(catalog_json)
        if len(uri) > 0:
            if uri[0] == 'BREWcatalog':
                resp = catalog_json
                if len(uri) > 1:
                    if uri[1] in catalog_dict:
                        resp = json.dumps(catalog_dict[uri[1]], indent=4)
                        user_dict = catalog_dict[uri[1]]
                        if len(uri) > 2:
                            if uri[2] == 'broker':
                                broker_dict = user_dict["broker"]
                                resp = json.dumps(broker_dict, indent=4)
                                pass
                            elif uri[2] == 'devices':
                                devices_list = user_dict['connected_devices']
                                resp = RetriveAllorOne('all', 'device', None, devices_list).retrive()
                                pass
                            elif uri[2] == 'specific_device' and len(uri) == 4:
                                devices_list = user_dict['connected_devices']
                                resp = RetriveAllorOne('one', 'device', uri[3], devices_list).retrive()
                                pass
                            elif uri[2] == 'services':
                                services_dict = user_dict[uri[2]]
                                resp = json.dumps(services_dict, indent=4)
                                if len(uri) > 3:
                                    if uri[3] in services_dict:
                                        stores_list = services_dict[uri[3]]
                                        resp = json.dumps({uri[3]: stores_list})
                                        pass
                                    else:
                                        if uri[3] == 'list':
                                            serv_list = []
                                            for key in services_dict:
                                                serv_list.append(key)
                                                pass
                                            resp = json.dumps({'services_list': serv_list})
                                            pass
                                        else:
                                            resp = json.dumps({'ERROR': 'ServiceNotFound'})
                                            pass
                                        pass
                                    pass
                                pass
                            elif uri[2] == 'user_information':
                                user_info = user_dict['user_information']
                                resp = json.dumps(user_info, indent=4)
                        pass
                    else:
                        resp = json.dumps({'ERROR': 'UserNotFound'})
                        pass
                    pass
                pass
            pass

        return resp

    def PUT(self,*uri):
        threadLock.acquire()
        file_catalog = open("catalog.json", "r")
        catalog_json = file_catalog.read()
        file_catalog.close()
        threadLock.release()
        catalog_dict = json.loads(catalog_json)
        flag = 0

        if len(uri) > 0:
            if uri[0] == 'BREWcatalog':
                if len(uri) > 1:
                    if uri[1] == 'add_new_user':
                        data = cherrypy.request.body.read()
                        data_dict = json.loads(data)
                        if 'user_information' in data_dict:
                            new_user = data_dict
                            new_infos = new_user['user_information']
                            catalog_dict[new_infos['userID']] = new_user
                            flag = 1
                            pass
                        pass
                    else:
                        if uri[1] in catalog_dict:
                            user_dict = catalog_dict[uri[1]]
                            if len(uri) > 2:
                                if uri[2] == 'add_new_device':
                                    data = cherrypy.request.body.read()
                                    data_dict = json.loads(data)
                                    if 'insert-timestamp' in data_dict and 'deviceID' in data_dict:
                                        devices_list = user_dict['connected_devices']
                                        new_dev = data_dict
                                        new_list = CatalogResearch(new_dev, 'deviceID', devices_list).search()
                                        user_dict['connected_devices'] = new_list
                                        catalog_dict[uri[1]] = user_dict
                                        flag = 1
                                        pass
                                    pass
                                elif uri[2] == 'broker':
                                    data = cherrypy.request.body.read()
                                    data_dict = json.loads(data)
                                    user_dict['broker'] = data_dict
                                    catalog_dict[uri[1]] = user_dict
                                    flag = 1
                                    pass
                                elif uri[2] == 'services':
                                    services_dict = user_dict['services']
                                    if len(uri) > 3:
                                        if uri[3] in services_dict:
                                            service_type = uri[3]
                                            data = cherrypy.request.body.read()
                                            data_dict = json.loads(data)
                                            if len(uri) > 4:
                                                if len(uri) > 5:
                                                    if uri[5] == 'update_tsh':
                                                        for device in services_dict[service_type]:
                                                            if uri[4] == device['deviceID']:
                                                                for resource in data_dict:
                                                                    if resource in device['thresholds']:
                                                                        device['thresholds'][resource] = data_dict[resource]
                                                                        flag = 1
                                                                        pass
                                                                    pass
                                                                pass
                                                            pass
                                                        user_dict['services'] = services_dict
                                                        catalog_dict[uri[1]] = user_dict
                                                        pass
                                                    elif uri[5] == 'update_active_res':
                                                        for device in services_dict[service_type]:
                                                            if uri[4] == device['deviceID']:
                                                                device['active_resources'] = data_dict['resources_list']
                                                                flag=1
                                                            pass
                                                        user_dict['services'] = services_dict
                                                        catalog_dict[uri[1]] = user_dict
                                                        pass
                                                    elif uri[5] == 'update_timings':
                                                        for device in services_dict[service_type]:
                                                            if uri[4] == device['deviceID']:
                                                                for resource in data_dict:
                                                                    if resource in device['timings']:
                                                                        device['timings'][resource] = data_dict[resource]
                                                                        flag = 1
                                                                        pass
                                                                    pass
                                                                pass
                                                            pass
                                                        user_dict['services'] = services_dict
                                                        catalog_dict[uri[1]] = user_dict
                                                    pass
                                                else:
                                                    new_list = CatalogResearch(data_dict, 'deviceID',services_dict[service_type]).search()
                                                    services_dict[service_type] = new_list
                                                    user_dict['services'] = services_dict
                                                    catalog_dict[uri[1]] = user_dict
                                                    flag = 1
                                                    pass
                                                pass
                                            else:
                                                services_dict[service_type] = data_dict[service_type]
                                                user_dict['services'] = services_dict
                                                catalog_dict[uri[1]] = user_dict
                                                flag = 1
                                                pass
                                            pass
                                        pass
                                    pass
                                pass
                            pass
                        pass
                    pass
                pass

        if flag == 1:
            threadLock.acquire()
            file_catalog = open("catalog.json", "w")
            file_catalog.write(json.dumps(catalog_dict, indent=4))
            file_catalog.close()
            threadLock.release()
            pass

        return

    def DELETE(self,*uri):
        threadLock.acquire()
        file_catalog = open("catalog.json", "r")
        catalog_json = file_catalog.read()
        file_catalog.close()
        threadLock.release()
        catalog_dict = json.loads(catalog_json)
        resp = ''
        if len(uri) == 3:
            if uri[0] == 'BREWcatalog' and uri[1] in catalog_dict:
                if uri[2] == 'delete_user':
                    resp = json.dumps(catalog_dict.pop(uri[1],None))
                    threadLock.acquire()
                    file_catalog = open("catalog.json", "w")
                    file_catalog.write(json.dumps(catalog_dict,indent=4))
                    file_catalog.close()
                    threadLock.release()
                    pass
                pass
            pass
        return resp


class RestCatalog(threading.Thread):
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

        cherrypy.tree.mount(CatalogManager(), '/', conf)

        cherrypy.config.update({'server.socket_host': '0.0.0.0'})
        cherrypy.config.update({'server.socket_port': 8080})

        cherrypy.engine.start()
        cherrypy.engine.block()

        return


class deviceRemover(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        return

    def run(self):
        while True:
            threadLock.acquire()
            self.file_catalog = open("catalog.json", "r")
            self.catalog_json = self.file_catalog.read()
            self.file_catalog.close()
            threadLock.release()
            self.catalog_dict = json.loads(self.catalog_json)
            for self.userID in self.catalog_dict:
                self.user=self.catalog_dict[self.userID]
                self.devices_list = self.user['connected_devices']
                self.i = 0

                while self.i < len(self.devices_list):
                    self.device = self.devices_list[self.i]
                    if time.time() > self.device['insert-timestamp'] + 120:
                        self.devices_list.pop(self.i)
                        pass
                    self.i += 1
                    pass

                self.user['connected_devices'] = self.devices_list
                self.catalog_dict[self.userID] = self.user

            self.catalog_json=json.dumps(self.catalog_dict, indent=4)
            threadLock.acquire()
            self.file_catalog = open("catalog.json", "w")
            self.file_catalog.write(self.catalog_json)
            self.file_catalog.close()
            threadLock.release()
            time.sleep(1)


threadLock = threading.Lock()

cat_rest_service = RestCatalog()
cat_device_remover = deviceRemover()

cat_rest_service.start()
cat_device_remover.start()






