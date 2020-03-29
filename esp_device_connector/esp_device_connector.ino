#include "DHT.h"
#include <ArduinoJson.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ESP8266HTTPClient.h>
#include <ESP8266WebServer.h>
#include <WiFiUdp.h>
#include <NTPClient.h>

#define DHTPIN 2 // pin D4

const char* catalog_addr = "http://192.168.43.19:8080/BREWcatalog/";

struct Topics {
  char event_notify[64];
  char manager[64];
};

struct Config {
  char user_owner[16];
  char deviceID[16];
  char end_point[64];
  char location[32];

  static const int maxResources = 2;
  char resources[maxResources][16];
  char units[maxResources][16];
  int time_steps[maxResources];
  Topics topics;

  void load(const JsonDocument&);
  void save(JsonDocument&) const;
};

Config config;

unsigned long currentMillis = 0;    // stores the value of millis() at each iteration of loop()
unsigned long previousConnectionUp = 60000;   // stores last time the connection with the catalog is updated
unsigned long previousTempSent = 0;   // stores last time the temperature is sent
unsigned long previousHumSent = 0;    // stores last time the humidity is sent

DHT dht(DHTPIN, DHT22);

WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "europe.pool.ntp.org");//, 0, 60000);

WiFiClient espClient;
PubSubClient client(espClient);
HTTPClient http;
ESP8266WebServer server(80);

void Config::load(const JsonDocument& obj) {
  strlcpy(user_owner, obj["user_owner"] | "", sizeof(user_owner));
  strlcpy(deviceID, obj["deviceID"] | "", sizeof(deviceID));
  strlcpy(end_point, obj["end_point"] | "", sizeof(end_point));
  strlcpy(location, obj["location"] | "", sizeof(location));

  // Extract each resource
  for (int res = 0; res <= maxResources - 1; res++) {
    strlcpy(resources[res], obj["resources"][res] | "", sizeof(resources[res]));
    strlcpy(units[res], obj["units"][res] | "", sizeof(units[res]));
    time_steps[res] = obj["time_steps"][res].as<int>();
  }

  strlcpy(topics.event_notify, obj["topics"]["event_notify"] | "", sizeof(topics.event_notify));
  strlcpy(topics.manager, obj["topics"]["manager"] | "", sizeof(topics.manager));
}

void Config::save(JsonDocument& obj) const {
  obj["user_owner"] = user_owner;
  obj["deviceID"] = deviceID;
  obj["end_point"] = end_point;
  obj["location"] = location;

  JsonArray resources_arr = obj.createNestedArray("resources");
  JsonArray units_arr = obj.createNestedArray("units");
  JsonArray time_steps_arr = obj.createNestedArray("time_steps");
  // Save each resource
  for (int res = 0; res <= maxResources - 1; res++) {
    resources_arr.add(resources[res]);
    units_arr.add(units[res]);
    time_steps_arr.add(time_steps[res]);
  }

  obj["topics"]["event_notify"] = topics.event_notify;
  obj["topics"]["manager"] = topics.manager;
}

bool loadConfig(String ip) {
  if (!SPIFFS.begin()) {
    Serial.println("Failed to mount file system");
    return false;
  }

  File configFile = SPIFFS.open("/device_connector_settings.json", "r");
  if (!configFile) {
    Serial.println("Failed to open config file");
    return false;
  }

  size_t size = configFile.size();
  if (size > 1024) {
    Serial.println("Config file size is too large");
    return false;
  }

  // Allocate a buffer to store contents of the file.
  std::unique_ptr<char[]> buf(new char[size]);

  configFile.readBytes(buf.get(), size);

  StaticJsonDocument<550> doc;
  auto error = deserializeJson(doc, buf.get());
  if (error) {
    Serial.println("Failed to parse config file");
    return false;
  }

  config.load(doc);

  // Setting the current endpoint
  String endpoint = "http://" + ip + "/rest";
  char endpoint_char[64];
  endpoint.toCharArray(endpoint_char, 64);
  strlcpy(config.end_point, endpoint_char, sizeof(config.end_point));

  Serial.print("User owner: ");
  Serial.println(config.user_owner);
  return true;
}

String WiFiConnect() {
  char* ssid = "Redmi7";
  char* password = "cacca1234";

  WiFi.begin(ssid, password);
  Serial.println("");
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("Connected to the WiFi network!");
  return WiFi.localIP().toString();
}

void MQTTconnect() {
  char url[100];
  strcpy(url, catalog_addr);
  strcat(url, config.user_owner);
  strcat(url, "/broker");
  
  if (http.begin(url)){
    int httpCode  = http.GET();
    if (httpCode  > 0) {
      Serial.print("Retrieving MQTT broker, GET request code: ");
      Serial.println(httpCode);
      if (httpCode == HTTP_CODE_OK || httpCode == HTTP_CODE_MOVED_PERMANENTLY) {
        String payload = http.getString();
        StaticJsonDocument<80> doc;
        auto error = deserializeJson(doc, payload);
        if (error) {
          Serial.println("Failed to parse broker info");
          return;
        }
        const char* mqttServer = doc["addr"];
        const int mqttPort = doc["port"];
        client.setServer(mqttServer, mqttPort);
        client.setCallback(callback);
        Serial.printf("Broker address: %s, Port: %d\n", mqttServer, mqttPort);
        Serial.print("Connecting to MQTT...");
        while (!client.connected()) {
          Serial.print(".");
          String clientId = "ESP8266Client-";
          clientId += String(random(0xffff), HEX);
          if (client.connect(clientId.c_str())) {
            Serial.println("Connected!");
            } else {
              Serial.print("Failed with state ");
              Serial.println(client.state());
              delay(2000);
            }
          }
        // client.subscribe(config.topics.manager);
        }
      } else {
        Serial.printf("[HTTP] GET broker failed, error: %s\n", http.errorToString(httpCode).c_str());
      }
    http.end();
  } else {
    Serial.print("[HTTP] GET broker failed");
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived in topic: ");
  Serial.println(topic);
 
  Serial.print("Message: ");
  for (int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
 
  Serial.println();
  Serial.println("-----------------------");
}

void handle_getTemp(){
  float t = dht.readTemperature();

  if (isnan(t)) {
    Serial.println("Failed to read temperature from DHT sensor!");
    return;
  }

  // Prepare a JSON payload string
  String temperature = String(t);
  String payload((char *)0);
  payload.reserve(32);
  payload += "{\"Temperature\":"; payload += temperature; payload += "}";

  // Send payload
  server.send(200, "text/plain", payload.c_str());
  
  // Just debug messages
  Serial.print("REST web server - GET Temperature ");
  Serial.print( "  ->  " );
  Serial.println(payload.c_str());
}

void handle_getHum(){
  float h = dht.readHumidity();

  if (isnan(h)) {
    Serial.println("Failed to read humidity from DHT sensor!");
    return;
  }

  // Prepare a JSON payload string
  String humidity = String(h);
  String payload((char *)0);
  payload.reserve(32);
  payload += "{\"Humidity\":"; payload += humidity; payload += "}";

  // Send payload
  server.send(200, "text/plain", payload.c_str());
  
  // Just debug messages
  Serial.print("REST web server - GET Humidity ");
  Serial.print( "  ->  " );
  Serial.println(payload.c_str());
}

void handle_NotFound(){
  server.send(404, "text/plain", "Not found");
}

void connectionUpdater() {
  // Update the connection to the catalog each 60s.
  if (currentMillis - previousConnectionUp >= 60000) {
    previousConnectionUp = currentMillis;

    char url[100];
    strcpy(url, catalog_addr);
    strcat(url, config.user_owner);
    strcat(url, "/add_new_device");

    StaticJsonDocument<550> doc;
    config.save(doc);
    unsigned long timestamp = timeClient.getEpochTime();
    doc["insert-timestamp"] = timestamp;
    serializeJsonPretty(doc, Serial);

    // Serialize the json
    String json;
    serializeJson(doc, json);

    http.begin(url);
    int httpResponseCode = http.PUT(json);
    if (httpResponseCode > 0) {
      Serial.print("Connection updater, PUT request code: ");
      Serial.println(httpResponseCode);
    } else {
      Serial.print("Error on sending PUT Request: ");
      Serial.println(httpResponseCode);
    }
    http.end();
  }
}

void sendTemperature() {
  if (currentMillis - previousTempSent >= config.time_steps[0] * 1000) {
    previousTempSent = currentMillis;

    // Read temperature as Celsius (the default)
    float t = dht.readTemperature();

    // Check if read failed and exit early (to try again).
    if (isnan(t)) {
      Serial.println("Failed to read temperature from DHT sensor!");
      return;
    }

    // Prepare a JSON payload string
    String temperature = String(t);
    unsigned long timestamp = timeClient.getEpochTime();
    String payload((char *)0);
    payload.reserve(100);
    payload += "{\"bn\":\""; payload += config.deviceID; payload += "\", \"e\":[{\"n\": \"Temperature\", \"u\":\"Cel\", \"t\":";
    payload += timestamp; payload += ", \"v\":"; payload += temperature; payload += "}]}";

    // Send payload
    client.publish(config.topics.event_notify, payload.c_str());

    // Just debug messages
    Serial.print("Temperature: ");
    Serial.print(t);
    Serial.print("*C, to Topic: ");
    Serial.print(config.topics.event_notify);
    Serial.print( "   ->   " );
    Serial.println(payload.c_str());
  }
}

void sendHumidity() {
  if (currentMillis - previousHumSent >= config.time_steps[1] * 1000) {
    previousHumSent = currentMillis;

    // Reading humidity
    float h = dht.readHumidity();

    // Check if read failed and exit early (to try again).
    if (isnan(h)) {
      Serial.println("Failed to read humidity from DHT sensor!");
      return;
    }

    // Prepare a JSON payload string
    String humidity = String(h);
    unsigned long timestamp = timeClient.getEpochTime();
    String payload((char *)0);
    payload.reserve(100);
    payload += "{\"bn\":\""; payload += config.deviceID; payload += "\", \"e\":[{\"n\": \"Humidity\", \"u\":\"%\", \"t\":";
    payload += timestamp; payload += ", \"v\":"; payload += humidity; payload += "}]}";

    // Send payload
    client.publish(config.topics.event_notify, payload.c_str());

    // Just debug messages
    Serial.print("Humidity: ");
    Serial.print(h);
    Serial.print("%, to Topic: ");
    Serial.print(config.topics.event_notify);
    Serial.print( "   ->   " );
    Serial.println(payload.c_str());
  }
}

void setup() {
  Serial.begin(115200);

  String ip = WiFiConnect();
  loadConfig(ip);
  timeClient.begin();
  dht.begin();
  MQTTconnect();
  // Starting the REST web server
  server.on("/rest/get_measure/Temperature", HTTP_GET, handle_getTemp);
  server.on("/rest/get_measure/Humidity", HTTP_GET, handle_getHum);
  server.onNotFound(handle_NotFound); 
  server.begin();
}

void loop() {
  while(!timeClient.update()) {
    timeClient.forceUpdate();
  }
  server.handleClient();
  currentMillis = millis();
  connectionUpdater();
  sendTemperature();
  sendHumidity();

  //client.loop();
}
