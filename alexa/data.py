SKILL_ID = "amzn1.ask.skill.5369fb88-22b5-4ae9-8063-98e7bf5ae1e7"

CATALOG_URL = "http://localhost:8080/BREWcatalog/"

USER_ID = "marioR92"

SKILL_TITLE = "Beer bot"

WELCOME_MESSAGE = (f"Welcome to {SKILL_TITLE}! "
                   "What would you like to know?")

EXIT_SKILL_MESSAGE = (f"Thank you for using {SKILL_TITLE}! "
                      "See you soon!")

REPROMPT = "What would you like to do now?"

HELP_MESSAGE = (
                "You can get information about measurements and thresholds for a specific device, "
                "asking a question like, get current temperature in dht11-a. "
                "I can also provide the list of the currently connected devices in the whole system "
                "or in a specific control process. "
                "What would you like to do?")

FALLBACK_ANSWER = (
    "Sorry. I can't help you with that. Try to refresh the connected devices list or "
    "ask for help to know what I can do.")

CONNECTED_DEVICES = ("Here is the list of connected devices: "
                     "<break strength='strong'/>"
                     "{}.")

NO_CONNECTED_DEVICES = "You have no connected devices."

CONNECTED_DEVICES_IN = ("Here is the list of connected devices in {}: "
                        "<break strength='strong'/>"
                        "{}.")

NO_CONNECTED_DEVICES_IN = "You have no connected devices in {}."

GET_MEASURE = "Measured {} in {} is {} {}."

RESOURCE_NOT_FOUND = "I am sorry. I think {} does not provide measurements for {}."

CONNECTION_ERR = ("I am really sorry. I am unable to get the "
                  "{} you want. Please try again later.")

GET_THRESHOLD = "{} threshold for {} is: <break strength='strong'/>" 

GET_THRESHOLDS = "{} thresholds for {} are: <break strength='strong'/>"  

MQTT_MSG = "{} threshold will be reached in {} {}."

NO_MQTT_MSG = "I am sorry. I didn't receive any message for {}."

MQTT_FAIL = "I am really sorry. It is not possible to establish an MQTT connection."
