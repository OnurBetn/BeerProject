import sys, os
from big_brother_classes import *


CATALOG_URL = "http://localhost:8080/BREWcatalog/"


class BeerManager:
    def __init__(self):
        # Menu actions

        self.main_menu_actions = {
            'this': self.main_menu,
            '1': self.sign_in,
            '2': self.sign_up,
            '0': self.exit,
        }
        self.access_menu_actions = {
            'this': self.access_obtained_menu,
            '1': self.set_broker,
            '2': self.set_devices,
            '3': self.set_services,
            '9': self.main_menu,
            '0': self.exit,
        }
        self.back_quit = {
            '9': self.access_obtained_menu,
            '0': self.exit,
        }
        self.set_services_actions = {
            'this': self.set_services,
            '1': self.add_service,
            '2': self.edit_service,
            '3': self.remove_service,
            '9': self.access_obtained_menu,
            '0': self.exit,
        }

        self.set_devices_actions = {
            'this': self.set_devices,
            '1': self.edit_id,
            '2': self.edit_location,
            '3': self.edit_resources,
            '4': self.edit_timesteps,
            '9': self.access_obtained_menu,
            '0': self.exit,
        }

        self.device_locations = {
            '1': 'storage_control',
            '2': 'fermentation_control',
            '3': 'mash_control'
        }
        self.device_resources = {
            '1': 'Temperature',
            '2': 'Humidity',
            '3': 'FluidTemp'
        }

        self.set_edit_service_actions = {
            'this': self.edit_service,
            '1': self.edit_service_id,
            '2': self.edit_service_resources,
            '3': self.edit_service_ths_steps,
            '4': self.edit_service_uncert_ranges,
            '5': self.edit_service_trend_flag,
            '9': self.access_obtained_menu,
            '0': self.exit,
        }

        self.username = None
        self.user_dict = None
        self.device_dict = None

    def main_menu(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        
        header = ""

        print(header)
        print("   Welcome,")
        print("   Please choose one of the following options:\n")
        print('\t [1] Sign in')
        print('\t [2] Sign up')
        print("\n\t [0] Quit")
        choice = input(" >>  ")
        self.exec_menu(self.main_menu_actions, choice)

    def exec_menu(self, menu_actions, choice):
        os.system('cls' if os.name == 'nt' else 'clear')

        ch = choice.lower()

        try:
            return menu_actions[ch]()
        except KeyError:
            print("Invalid selection, please try again.\n")
            menu_actions['this']()

    def sign_in(self):
        print("  --------------- Sign in ---------------\n\n")
        while True:
            print(" Insert your username:")
            self.username = input(" >>  ")
            self.user_dict = requests.get(CATALOG_URL + self.username).json()
            # Check if the user exists
            if 'ERROR' not in self.user_dict:
                password = self.user_dict['user_information']['password']
                break
            else:
                print(" Username not registered in the system. Try again!")
        
        while True:
            print(" Insert your password:")
            typed_password = input(" >>  ")
            # Check if the password is correct 
            if typed_password == password:
                break
            else:
                print(" Wrong password. Try again!")

        self.access_obtained_menu()

    def sign_up(self):
        print("  --------------- Sign up ---------------\n")
        while True:
            print(" Insert your username:")
            username = input(" >>  ")
            # Check if the username is already taken
            user_info = requests.get(CATALOG_URL + username + '/user_information').json()
            if 'ERROR' not in user_info:
                print(" Sorry this username is already taken. Try with another one!")
            else:
                break

        print(" Insert your email address:")
        email = input(" >>  ")
        print(" Insert your password:")
        password = input(" >>  ")

        user_dict = {
                        "broker": {},
                        "connected_devices": [],
                        "user_information": {
                            "userID": username,
                            "email_address": email,
                            "password": password
                        },
                        "services": {
                            "fermentation_control": [],
                            "mash_control": [],
                            "storage_control": []
                        }
                    }
        body = json.dumps(user_dict)
        response = requests.put(CATALOG_URL + 'add_new_user', body)
        if response.status_code == 200:
            print(" Congratulations, you are registered to the system!")
        else:
            response.raise_for_status()

        print("\n\t [9] Back")
        print("\t [0] Quit")
        choice = input(" >>  ")
        self.exec_menu(self.main_menu_actions, choice)

    def access_obtained_menu(self):
        os.system('cls' if os.name == 'nt' else 'clear')

        print(f"  --------------- Access obtained as: {self.username} ---------------\n\n")
        print("   Welcome,")
        print("   Please choose one of the following options:\n")
        print('\t [1] Set broker')
        print('\t [2] Set device settings')
        print('\t [3] Set services')
        print("\n\t [9] Back to main menu")
        print("\t [0] Quit")
        choice = input(" >>  ")
        self.exec_menu(self.access_menu_actions, choice)

    def set_broker(self):
        set_b = SetBroker()
        self.user_dict = requests.get(CATALOG_URL + self.username).json()
        if not self.user_dict["connected_devices"]:
            print("  --------------- Set broker ---------------\n")
            print(" Insert broker address:")
            broker_addr = input(" >>  ")

            while True:
                print(" Insert broker port:")
                port = input(" >>  ")
                try:
                    port = int(port)
                    break
                except ValueError:
                    print(" Port should be an integer. Try again!")

            rc = set_b.verify(broker_addr, port)
            if rc == 0:
                print('VALID message broker')
                body = json.dumps({"addr": broker_addr, "port": port})
                response = requests.put(CATALOG_URL + self.user_dict['user_information']['userID'] + '/broker', body)
                if response.status_code == 200:
                    print(" Broker updated!")
                else:
                    response.raise_for_status()
                pass
            elif rc == 10:
                print('INVALID message broker')
                pass
            else:
                print(f'Connection problems: rc={rc}')
                pass
            pass
        else:
            print('Devices currently connected: Unable to update broker settings')
            pass

        print("\n\t [9] Back")
        print("\t [0] Quit")
        choice = input(" >>  ")
        self.exec_menu(self.back_quit, choice)
        

    ### Devices settings ###
    
    def edit_id(self):
        if self.device_dict is not None:
            print(f"Current device ID: {self.device_dict['deviceID']}\n")
            while True:
                new_id = input("Insert a new ID: ")
                if " " not in new_id:
                    break
                else:
                    print('The ID must be continous, try again!')
                    pass
                pass
            self.device_dict['deviceID'] = new_id
            self.device_dict['topics'] = EditDeviceTools().topics(self.device_dict['topics'],new_id,'deviceID')
            body = json.dumps(self.device_dict)
            response = requests.put(self.device_dict['end_point']+'/update_settings',body)
            if response.status_code == 200:
                print("Device ID updated")
            else:
                print("Something is gone wrong. ID update failed...\n")
                pass
            pass
        else:
            print("Action not allowed")
            pass
        return

    def edit_location(self):
        if self.device_dict is not None:
            print(f"Current device location: {self.device_dict['location']}\n")
            print("Select a new location:\n")
            print('\t [1] storage_control')
            print('\t [2] fermentation_control')
            print('\t [3] mash_control')
            while True:
                choice = input(" >>  ")
                try:
                    new_location = self.device_locations[choice]
                    break
                except KeyError:
                    print("Invalid selection, please try again.\n")
                pass
            self.device_dict['location'] = new_location
            self.device_dict['topics'] = EditDeviceTools().topics(self.device_dict['topics'], new_location, 'location')
            body = json.dumps(self.device_dict)
            response = requests.put(self.device_dict['end_point'] + '/update_settings',body)
            if response.status_code == 200:
                print("Device location updated")
            else:
                print("Something is gone wrong. Location update failed...\n")
                pass
            pass
        else:
            print("Action not allowed")
            pass
        return

    def edit_timesteps(self):
        if self.device_dict['time_steps']:
            select_dict = {}
            i = 1
            print(f"Select one of the following resources measuring time steps:\n")
            for res in list(self.device_dict['time_steps']):
                print(f"\t [{i}] {res} : {self.device_dict['time_steps'][res]} sec")
                select_dict[str(i)] = res
                i += 1
                pass
            while True:
                choice = input(" >>  ")
                try:
                    chosen_res = select_dict[choice]
                    break
                except KeyError:
                    print("Invalid selection, please try again.\n")
                pass
            print(f"Please insert a new measuring time steps for {chosen_res} (sec):\n")
            while True:
                choice2 = input(" >>  ")
                if choice2.isnumeric():
                    break
                else:
                    print("Invalid selection, it must be a number.\n")
                pass
            self.device_dict['time_steps'][chosen_res] = int(choice2)
            body = json.dumps(self.device_dict)
            response = requests.put(self.device_dict['end_point'] + '/update_settings', body)
            if response.status_code == 200:
                print("Device measuring time steps updated")
            else:
                print("Something is gone wrong. Time steps update failed...\n")
                pass
            pass
        else:
            print('No internal resource')
            pass
        return

    def edit_resources(self):
        flag_noupdate = 0
        if self.device_dict is not None:
            print("Select one action: ")
            print("\t [a] If you want to ADD a new resource")
            print("\t [d] If you want to DELETE a resource")
            while True:
                choice1 = input(" >>  ")
                if choice1 == 'a' or choice1 == 'd':
                    break
                else:
                    print("Invalid selection, please try again.\n")
                    pass
                pass
            if choice1 == 'd':
                i = 1
                select_dict = {}
                if self.device_dict['resources']:
                    print("Select one of the current device resources:")
                    for res in self.device_dict['resources']:
                        print(f'\t [{i}] {res}')
                        select_dict[str(i)] = res
                        i += 1
                        pass
                    while True:
                        choice2 = input(" >>  ")
                        try:
                            del_res = select_dict[choice2]
                            break
                        except KeyError:
                            print("Invalid selection, please try again.\n")
                        pass
                    del_ind = self.device_dict['resources'].index(del_res)
                    self.device_dict['resources'].pop(del_ind)
                    self.device_dict['device_pins'] = EditDeviceTools().pins(self.device_dict['device_pins'], del_res,choice1, self.device_dict['deviceType'])
                    self.device_dict['units'] = EditDeviceTools().units(self.device_dict['units'], del_res, choice1)
                    self.device_dict['time_steps'] = EditDeviceTools().timesteps(self.device_dict['time_steps'],del_res,choice1)
                    pass
                else:
                    print('No internal resource')
                    flag_noupdate = 1
                pass

            elif choice1 == 'a':
                print("Select a new resource:")
                for res in self.device_resources:
                    print(f'\t [{res}] {self.device_resources[res]}')
                    pass
                while True:
                    choice2 = input(" >>  ")
                    try:
                        new_res = self.device_resources[choice2]
                        break
                    except KeyError:
                        print("Invalid selection, please try again.\n")
                    pass
                if new_res in self.device_dict['resources']:
                    print("Resource already present in your device\n")
                    flag_noupdate = 1
                    pass
                else:
                    self.device_dict['resources'].append(new_res)
                    self.device_dict['device_pins'] = EditDeviceTools().pins(self.device_dict['device_pins'],new_res,choice1,self.device_dict['deviceType'])
                    self.device_dict['units'] = EditDeviceTools().units(self.device_dict['units'],new_res,choice1)
                    self.device_dict['time_steps'] = EditDeviceTools().timesteps(self.device_dict['time_steps'], new_res, choice1)
                pass
            if flag_noupdate == 0:
                body = json.dumps(self.device_dict)
                response = requests.put(self.device_dict['end_point'] + '/update_settings', body)
                if response.status_code == 200:
                    print("Device resources updated")
                else:
                    print("Something is gone wrong. Resources update failed...\n")
                    pass
                pass
            pass
        else:
            print("Action not allowed")
            pass
        return

    def set_devices(self):
        print("  --------------- Set devices ---------------\n")
        self.user_dict = requests.get(CATALOG_URL + self.username).json()

        if self.user_dict["connected_devices"]:
            print(f"Please choose one of the following devices:\n")
            i = 1
            select_dict = {}
            for dev in self.user_dict["connected_devices"]:
                select_dict[str(i)] = dev
                print(f"[{i}] {dev['deviceID']}")
                i += 1
                pass

            while True:
                choice = input(" >>  ")
                try:
                    self.device_dict = select_dict[choice]
                    break
                except KeyError:
                    print("Invalid selection, please try again.\n")
                pass

            self.device_dict.pop('insert-timestamp')
            dev_status = self.search_dev_in_services(self.device_dict['deviceID'],self.user_dict['services'])

            if dev_status is None:
                print(f"Selected device: {self.device_dict['deviceID']}\n")
                print('\t [1] Edit device ID')
                print('\t [2] Edit device location')
                print('\t [3] Edit device resources')
                print('\t [4] Edit measure time steps')

                choice = input(" >>  ")
                self.exec_menu(self.set_devices_actions, choice)
                pass
            else:
                print("The device is up and running. It can't be edited\n")
            pass

        else:
            print(f"No connected devices\n")
            pass

        print("\n\t [9] Back")
        print("\t [0] Quit")
        choice = input(" >>  ")
        self.exec_menu(self.back_quit, choice)

    def search_dev_in_services(self,devID,services_dict):
        status = None
        for service in services_dict:
            units_list = services_dict[service]
            if status is None:
                for unit in units_list:
                    if devID == unit['deviceID']:
                        status = unit['status']
                        break
                    pass
                pass
            pass

        return status


    # Services settings #

    def set_services(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("  --------------- Set services ---------------\n")

        print('\t [1] Add a new service')
        print('\t [2] Edit a service')
        print('\t [3] Remove a service')
        print("\n\t [9] Back")
        print("\t [0] Quit")

        choice = input(" >>  ")
        self.exec_menu(self.set_services_actions, choice)

    def edit_service_id(self):
        while True:
            dev_id = input("Insert the ID of the device related to the service: ")
            if " " not in dev_id:
                break
            else:
                print('  The ID must be continous, try again!')
        return dev_id

    def edit_service_resources(self):
        print("Select the resources typing a list of numbers separated by whitespaces:")
        for res in self.device_resources:
            print(f'\t [{res}] {self.device_resources[res]}')
        while True:
            choice = input(" >>  ")
            keys = choice.split()
            try:
                resources = [self.device_resources[key] for key in keys]
                break
            except KeyError:
                print("  Invalid selection, please try again.")
                print("  Insert a list of numbers separated by whitespaces.")
        return resources

    def edit_service_ths_steps(self, resources):
        ths_times = {}
        for res in resources:
            print(f"Insert the number of thresholds steps for {res}:")
            while True:
                choice = input(" >>  ")
                if choice.isnumeric():
                    n = int(choice)
                    ths_times[res] = [0] * n
                    break
                else:
                    print("  Invalid input, it must be an integer.")
        return ths_times

    def edit_service_uncert_ranges(self, resources):
        uncertainty = {}
        for res in resources:
            print(f"Insert the uncertainty range for {res}:")
            while True:
                choice = input(" >>  ")
                if choice.isnumeric():
                    n = int(choice)
                    uncertainty[res] = n
                    break
                else:
                    print("  Invalid input, it must be an integer.")
        return uncertainty

    def edit_service_trend_flag(self):
        print(f"Does the service provide some trends information? (0:no, 1:yes):")
        while True:
            choice = input(" >>  ")
            if choice == '0' or choice == '1':
                trend_flag = int(choice)
                break
            else:
                print("  Invalid input, it must be 0 or 1.")
        return trend_flag

    def add_service(self):
        print("  --------------- Add service ---------------\n")
        # Location choice
        print("Select the location of the new service:\n")
        for loc in self.device_locations:
            print(f'\t [{loc}] {self.device_locations[loc]}')
        while True:
            choice = input(" >>  ")
            try:
                location = self.device_locations[choice]
                break
            except KeyError:
                print("  Invalid selection, please try again.")

        # ID choice
        dev_id = self.edit_service_id()

        # Resources choice
        resources = self.edit_service_resources()

        # Number of steps choice
        ths_times = self.edit_service_ths_steps(resources)

        # Uncertainty ranges choice
        uncertainty = self.edit_service_uncert_ranges(resources)

        # Trend choice
        trend_flag = self.edit_service_trend_flag()
        
        service_dict = {
                            "deviceID": dev_id,
                            "active_resources": resources,
                            "thresholds": ths_times,
                            "incert_ranges": uncertainty,
                            "timings": ths_times,
                            "trend_flag": trend_flag,
                            "status": 2
                        }

        body = json.dumps(service_dict)
        response = requests.put(CATALOG_URL + self.username + '/services/' + location + '/' + dev_id,
                                body)
        if response.status_code == 200:
            print(" Service added!")
        else:
            response.raise_for_status()
        print("\n\t [9] Back")
        print("\t [0] Quit")
        choice = input(" >>  ")
        self.exec_menu(self.back_quit, choice)
        
    def edit_service(self):
        print("  --------------- Edit service ---------------\n")
        print("   Please choose the service you want to edit:\n")
        services = self.current_services()
        print("\n  [0] Back")
        while True:
            try:
                choice = int(input(" >>  "))
                if choice <= len(services):
                    break
                else:
                    print(f" Max accepted value is {len(services)}. Try again!")
            except ValueError:
                print(" Insert an integer. Try again!")
        
        devID_to_edit = services[choice]
        for loc,service in self.user_dict['services'].items():
            for dev in service:
                if dev['deviceID'] == devID_to_edit:
                    service_to_edit = dev
                    location = loc
                    
        if service_to_edit['status'] != 2:
            print("The service is currently active. It can't be edited.\n")
        else:
            print('\t [1] Edit resources')
            print('\t [2] Edit number of thresholds steps')
            print('\t [3] Edit uncertainty ranges')
            print('\t [4] Edit trend flag')
            print("\n\t [9] Back")
            print("\t [0] Quit")

            choice = input(" >>  ")

            if choice == '1':
                resources = self.edit_service_resources()
                service_to_edit['active_resources'] = resources
                service_to_edit['thresholds'] = self.edit_service_ths_steps(resources)
                service_to_edit['timings'] = service_to_edit['thresholds']
                service_to_edit['incert_ranges'] = self.edit_service_uncert_ranges(resources)
            elif choice == '2':
                resources = service_to_edit['active_resources']
                service_to_edit['thresholds'] = self.edit_service_ths_steps(resources)
                service_to_edit['timings'] = service_to_edit['thresholds']
            elif choice == '3':
                resources = service_to_edit['active_resources']
                service_to_edit['incert_ranges'] = self.edit_service_uncert_ranges(resources)
            elif choice == '4':
                service_to_edit['trend_flag'] = self.edit_service_trend_flag()

            body = json.dumps(service_to_edit)
            response = requests.put(CATALOG_URL + self.username + '/services/' + location + '/' + devID_to_edit,
                                    body)
            if response.status_code == 200:
                print(" Service edited!")
            else:
                response.raise_for_status()
                
        print("\n\t [9] Back")
        print("\t [0] Quit")
        choice = input(" >>  ")
        self.exec_menu(self.back_quit, choice)

    def remove_service(self):
        print("  --------------- Remove service ---------------\n")
        print("   Please choose the service you want to remove:\n")
        services = self.current_services()
        print("\n  [0] Back")
        while True:
            try:
                choice = int(input(" >>  "))
                if choice <= len(services):
                    break
                else:
                    print(f" Max accepted value is {len(services)}. Try again!")
            except ValueError:
                print(" Insert an integer. Try again!")
        
        devID_to_remove = services[choice]

        for _, service_list in self.user_dict['services'].items():
            service_list[:] = [i for i in service_list if i['deviceID'] != devID_to_remove] 

        body = json.dumps(self.user_dict)
        response = requests.put(CATALOG_URL + 'add_new_user', body)
        if response.status_code == 200:
            print(" Service removed!")
        else:
            response.raise_for_status()

        print("\n\t [9] Back")
        print("\t [0] Quit")
        choice = input(" >>  ")
        self.exec_menu(self.back_quit, choice)

    def current_services(self):
        self.user_dict = requests.get(CATALOG_URL + self.username).json()
        i = 0
        services_dict = {}
        for service in self.user_dict['services']:
            print(' * ' + service + ':')
            for device in self.user_dict['services'][service]:
                i += 1
                print(f"\t[{i}] {device['deviceID']}")
                services_dict[i] = device['deviceID']
        return services_dict


    def exit(self):
        sys.exit()


if __name__ == "__main__":
    manager = BeerManager()
    manager.main_menu()
