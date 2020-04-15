import requests
from data import CATALOG_URL, USER_ID

from num2words import num2words
from ask_sdk_model.dialog import DynamicEntitiesDirective
from ask_sdk_model.er.dynamic import UpdateBehavior, EntityListItem, Entity, EntityValueAndSynonyms
from ask_sdk_model.slu.entityresolution import StatusCode


def understand(process):
    if "storage" in process.lower():
        return "storage_control"
    elif "mash" in process.lower():
        return "mash_control"
    else:
        return "fermentation_control"


def get_connected_devices():
    conn_devs = http_get(CATALOG_URL + USER_ID + '/devices')['device']
    return conn_devs


def get_thresholds_timings(service_type, deviceID):
    services = http_get(CATALOG_URL + USER_ID + '/services/' + service_type)[service_type]
    service = next((dev for dev in services if dev['deviceID'] == deviceID))
    thresholds = service['thresholds']
    timings = service['timings']
    return thresholds, timings


def http_get(url, path_params=None):
    """Return a response JSON for a GET call from `request`."""
    response = requests.get(url=url, params=path_params)

    if response.status_code < 200 or response.status_code >= 300:
        response.raise_for_status()
    return response.json()


def refresh_devices_slot(devices):
    entities = []
    for deviceID in devices:
        entity_synonyms = EntityValueAndSynonyms(
            value=deviceID, synonyms=evaluate_synonyms(deviceID)
        )
        entities.append(Entity(id=deviceID, name=entity_synonyms))

    replace_entity_directive = DynamicEntitiesDirective(
            update_behavior=UpdateBehavior.REPLACE,
            types=[EntityListItem(name="DEVICE", values=entities)],
        )

    return replace_entity_directive


def evaluate_synonyms(deviceID):
    synonyms = ["", "", ""]   
    for ind, char in enumerate(deviceID):
        if char.isalpha():
            synonyms[0] += char
            synonyms[1] += char + '. '
            synonyms[2] += char + ' '
        elif char.isdecimal() and deviceID[ind-1].isdecimal():
            num_to_word = num2words(deviceID[ind-1] + char)
            synonyms[0] += " " + num_to_word + " "
            synonyms[1] += num_to_word + " "
            synonyms[2] += num_to_word + " "
    return synonyms


def get_slot_values(filled_slots):
    """Return slot values with additional info."""
    slot_values = {}

    for _, slot_item in filled_slots.items():
        name = slot_item.name
        resolutions_per_authority = slot_item.resolutions.resolutions_per_authority
        for r in resolutions_per_authority:
            try:
                status_code = r.status.code

                if status_code == StatusCode.ER_SUCCESS_MATCH:
                    slot_values[name] = {
                        "synonym": slot_item.value,
                        "resolved": r.values[0].value.name,
                        "is_validated": True,
                    }
                    break
                elif status_code == StatusCode.ER_SUCCESS_NO_MATCH:
                    slot_values[name] = {
                        "synonym": slot_item.value,
                        "resolved": slot_item.value,
                        "is_validated": False,
                    }
                else:
                    pass
            except (AttributeError, ValueError, KeyError, IndexError, TypeError):
                slot_values[name] = {
                    "synonym": slot_item.value,
                    "resolved": slot_item.value,
                    "is_validated": False,
                }
    return slot_values
