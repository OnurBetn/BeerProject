import json
from MyMQTT import MyMQTT

class CatalogResearch(object):
    def __init__(self,new_dict,keyword,list_dict):
        self.new = new_dict
        self.key = keyword
        self.list = list_dict
        return

    def search(self):

        self.i = 0
        self.flag = 0
        while self.i < len(self.list):
            self.dict = self.list[self.i]
            if self.new[self.key] == self.dict[self.key]:
                self.list[self.i] = self.new
                self.flag = 1
                pass
            self.i += 1
            pass
        if self.flag == 0:
            self.list.append(self.new)
            pass
        return self.list

class RetriveAllorOne(object):
    def __init__(self,quantity,type,specific_ID,list):
        self.quantity=quantity
        self.specific_ID=specific_ID
        self.type=type
        self.list=list
        return

    def retrive(self):
        self.resp=None
        if self.quantity == 'all':
            self.resp = json.dumps({self.type:self.list},indent=4)
            pass
        elif self.quantity == 'one':
            if self.type=='user':
                self.type='userID'
                pass
            elif self.type=='device':
                self.type='deviceID'
                pass
            self.flag = 0
            if len(self.list)!=0:
                for self.element in self.list:
                    if self.element[self.type] == self.specific_ID:
                        self.resp = json.dumps(self.element, indent=4)
                        self.flag = 1
                        pass
                    pass
            if self.flag == 0:
                self.resp = json.dumps({'ERROR':'DeviceNotFound'})
                pass
            pass
        return self.resp

