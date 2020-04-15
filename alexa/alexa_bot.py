import logging
import time

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler, AbstractExceptionHandler,
    AbstractResponseInterceptor, AbstractRequestInterceptor)
from ask_sdk_core.utils import is_intent_name, is_request_type
from ask_sdk_model import Response

from flask_ask_sdk.skill_adapter import SkillAdapter
from flask import Flask

import data, util
from MyMQTT import MyMQTT


# Skill Builder object
sb = SkillBuilder()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Request Handler classes
class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for skill launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In LaunchRequestHandler")

        connected_devices = util.get_connected_devices()
        conn_devicesID = [dev["deviceID"] for dev in connected_devices]

        broker = util.http_get(data.CATALOG_URL + data.USER_ID + '/broker')

        attr = handler_input.attributes_manager.session_attributes
        attr["connected_devices"] = connected_devices
        attr["broker"] = broker
        handler_input.attributes_manager.session_attributes = attr

        handler_input.response_builder.speak(data.WELCOME_MESSAGE).ask(
            data.HELP_MESSAGE).add_directive(util.refresh_devices_slot(conn_devicesID))
        return handler_input.response_builder.response


class GetConnectedDevices(AbstractRequestHandler):
    """ Handler to get the currently connected devices (in a process)."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("GetConnectedDevices")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        response_builder = handler_input.response_builder
        process = handler_input.request_envelope.request.intent.slots["Process"].value
        connected_devices = util.get_connected_devices()
        conn_devicesID = [dev["deviceID"] for dev in connected_devices]

        if process:
            proc = util.understand(process)
            conn_devicesID_proc = [dev["deviceID"] for dev in connected_devices if dev['location'] == proc]
            if conn_devicesID_proc:
                devices_string = " ".join(conn_devicesID_proc)
                speech = data.CONNECTED_DEVICES_IN.format(process, devices_string)
            else:
                speech = data.NO_CONNECTED_DEVICES_IN.format(process)
        else:
            if conn_devicesID:
                devices_string = " ".join(conn_devicesID)
                speech = data.CONNECTED_DEVICES.format(devices_string)
            else:
                speech = data.NO_CONNECTED_DEVICES

        attr = handler_input.attributes_manager.session_attributes
        attr["connected_devices"] = connected_devices
        handler_input.attributes_manager.session_attributes = attr

        response_builder.speak(speech)
        response_builder.ask(data.REPROMPT)
        response_builder.add_directive(util.refresh_devices_slot(conn_devicesID))

        return response_builder.response


class GetMeasures(AbstractRequestHandler):
    """ Handler to get the current measures in a device."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("GetMeasures")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        response_builder = handler_input.response_builder
        attr = handler_input.attributes_manager.session_attributes
        filled_slots = handler_input.request_envelope.request.intent.slots
        slot_values = util.get_slot_values(filled_slots)

        conn_devs = attr["connected_devices"]
        device = slot_values["Device"]["resolved"]
        resource = slot_values["Resource"]["resolved"]
        dev = next((dev for dev in conn_devs if dev['deviceID'] == device), None) 
        end_point = dev["end_point"]
        units = dev["units"]   

        try:
            measure = util.http_get(end_point + '/get_measure/' + resource)[resource]
            if measure:
                speech = data.GET_MEASURE.format(resource, device, measure, units[resource])
            else:
                speech = data.RESOURCE_NOT_FOUND.format(device, resource)
        except:
            speech = data.CONNECTION_ERR.format("measure")
        
        response_builder.speak(speech)
        response_builder.ask(data.REPROMPT)
        return response_builder.response


class GetThresholds(AbstractRequestHandler):
    """ Handler to get the current thresholds and timings in a device."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("GetThresholds")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        response_builder = handler_input.response_builder
        attr = handler_input.attributes_manager.session_attributes
        filled_slots = handler_input.request_envelope.request.intent.slots
        slot_values = util.get_slot_values(filled_slots)

        conn_devs = attr["connected_devices"]
        device = slot_values["Device"]["resolved"]
        resource = slot_values["Resource"]["resolved"]
        dev = next((dev for dev in conn_devs if dev['deviceID'] == device), None) 
        location = dev["location"]
        units = dev["units"]    

        try:
            ths, timings = util.get_thresholds_timings(location, device)
            if resource in ths:
                if len(ths[resource]) > 1:
                    speech = data.GET_THRESHOLDS.format(resource, device)
                else:
                    speech = data.GET_THRESHOLD.format(resource, device)
                for t in range(len(ths[resource])):
                    if timings[resource][t]:
                        speech += f'{ths[resource][t]} {units[resource]} for {timings[resource][t]} minutes.\n'
                    else:
                        speech += f'{ths[resource][t]} {units[resource]}.\n'
            else:
                speech = data.RESOURCE_NOT_FOUND.format(device, resource)
        except:
            speech = data.CONNECTION_ERR.format("thresholds")
        
        response_builder.speak(speech)
        response_builder.ask(data.REPROMPT)
        return response_builder.response


class TimeToThreshold(AbstractRequestHandler):
    """ Handler to get the current measures in a device."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("TimeToThreshold")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        response_builder = handler_input.response_builder
        attr = handler_input.attributes_manager.session_attributes
        filled_slots = handler_input.request_envelope.request.intent.slots
        slot_values = util.get_slot_values(filled_slots)

        conn_devs = attr["connected_devices"]
        broker = attr["broker"]
        device = slot_values["Device"]["resolved"]
        self.resource = slot_values["Resource"]["resolved"]
        dev = next((dev for dev in conn_devs if dev['deviceID'] == device), None) 
        topic = dev["topics"]["analytics"]  

        try:
            tsh_handler = MyMQTT('Alexa_Bot_'+data.USER_ID, broker['addr'], broker['port'], self)
            tsh_handler.start()
            tsh_handler.mySubscribe(topic)
            self.speech = None

            # Wait 5 seconds to receive messages
            t_end = time.time() + 5
            while time.time() < t_end:
                time.sleep(1)
            tsh_handler.stop()
            
            if self.speech is None:
                self.speech = data.NO_MQTT_MSG.format(device)
        except:
            self.speech = data.MQTT_FAIL
        
        response_builder.speak(self.speech)
        response_builder.ask(data.REPROMPT)
        return response_builder.response

    def notify(self, topic, msg):
        for event in msg['e']:
            if event['n'] == self.resource + "/time_to_tsh":
                self.speech = data.MQTT_MSG.format(self.resource, event['v'], event['u'])


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for skill session end."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In SessionEndedRequestHandler")
        print("Session ended with reason: {}".format(
            handler_input.request_envelope))
        return handler_input.response_builder.response


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for help intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In HelpIntentHandler")
        handler_input.attributes_manager.session_attributes = {}
        # Resetting session

        handler_input.response_builder.speak(
            data.HELP_MESSAGE).ask(data.HELP_MESSAGE)
        return handler_input.response_builder.response


class ExitIntentHandler(AbstractRequestHandler):
    """Single Handler for Cancel, Stop and Pause intents."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input) or
                is_intent_name("AMAZON.PauseIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In ExitIntentHandler")
        handler_input.response_builder.speak(
            data.EXIT_SKILL_MESSAGE).set_should_end_session(True)
        return handler_input.response_builder.response


class FallbackIntentHandler(AbstractRequestHandler):
    """Handler for handling fallback intent.
     2018-May-01: AMAZON.FallackIntent is only currently available in
     en-US locale. This handler will not be triggered except in that
     locale, so it can be safely deployed for any locale."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")
        handler_input.response_builder.speak(
            data.FALLBACK_ANSWER).ask(data.HELP_MESSAGE)

        return handler_input.response_builder.response


# Exception Handler classes
class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Catch All Exception handler.
    This handler catches all kinds of exceptions and prints
    the stack trace on AWS Cloudwatch with the request envelope."""
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speech = "Sorry, there was some problem. Please try again!"
        handler_input.response_builder.speak(speech).ask(speech)

        return handler_input.response_builder.response


# Request and Response Loggers
class RequestLogger(AbstractRequestInterceptor):
    """Log the request envelope."""
    def process(self, handler_input):
        # type: (HandlerInput) -> None
        logger.info("Request Envelope: {}".format(
            handler_input.request_envelope))


class ResponseLogger(AbstractResponseInterceptor):
    """Log the response envelope."""
    def process(self, handler_input, response):
        # type: (HandlerInput, Response) -> None
        logger.info("Response: {}".format(response))


# Add all request handlers to the skill.
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(GetConnectedDevices())
sb.add_request_handler(GetMeasures())
sb.add_request_handler(GetThresholds())
sb.add_request_handler(TimeToThreshold())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(ExitIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(FallbackIntentHandler())

# Add exception handler to the skill.
sb.add_exception_handler(CatchAllExceptionHandler())

# Add response interceptor to the skill.
sb.add_global_request_interceptor(RequestLogger())
sb.add_global_response_interceptor(ResponseLogger())

app = Flask(__name__)

skill_response = SkillAdapter(
    skill=sb.create(), skill_id=data.SKILL_ID, app=app)

skill_response.register(app=app, route="/")

if __name__ == '__main__':
    app.run()
