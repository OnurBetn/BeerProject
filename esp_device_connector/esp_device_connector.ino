#include "DHT.h"
#include <ArduinoJson.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ESP8266HTTPClient.h>
#include <ESP8266WebServer.h>
#include <WiFiUdp.h>
#include <NTPClient.h>

#define ssid "Redmi7"
#define password "cacca1234"
#define mqttServer "test.mosquitto.org"
#define mqttPort 1883
#define N_RESOURCES 2
#define DHTPIN 2 // pin D4

const char* catalog_addr = "http://192.168.43.19:8080/BREWcatalog/";

struct Units {
  char unit[N_RESOURCES][8];
};

struct Topics {
  char event_notify[64];
  char manager[64];
  char analytics[64];
};

struct Time_steps {
  char t_s[N_RESOURCES];
};

struct Config {
  char user_owner[16];
  char deviceID[16];
  char end_point[64];
  char location[32];

  char resources[N_RESOURCES][16];
  Units units;
  Time_steps time_steps;
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

  // Load each resource
  for (int i = 0; i <= N_RESOURCES - 1; i++) {
    strlcpy(resources[i], obj["resources"][i] | "", sizeof(resources[i]));
    strlcpy(units.unit[i], obj["units"][resources[i]] | "", sizeof(units.unit[i]));
    time_steps.t_s[i] = obj["time_steps"][resources[i]].as<int>();
  }

  strlcpy(topics.event_notify, obj["topics"]["event_notify"] | "", sizeof(topics.event_notify));
  strlcpy(topics.manager, obj["topics"]["manager"] | "", sizeof(topics.manager));
  strlcpy(topics.analytics, obj["topics"]["analytics"] | "", sizeof(topics.analytics));
}

void Config::save(JsonDocument& obj) const {
  obj["user_owner"] = user_owner;
  obj["deviceID"] = deviceID;
  obj["end_point"] = end_point;
  obj["location"] = location;

  JsonArray resources_arr = obj.createNestedArray("resources");
  JsonObject units_obj = obj.createNestedObject("units");
  JsonObject time_steps_obj = obj.createNestedObject("time_steps");
  // Save each resource
  for (int i = 0; i <= N_RESOURCES - 1; i++) {
    resources_arr.add(resources[i]);
    units_obj[resources[i]] = units.unit[i];
    time_steps_obj[resources[i]] = time_steps.t_s[i];
  }

  obj["topics"]["event_notify"] = topics.event_notify;
  obj["topics"]["manager"] = topics.manager;
  obj["topics"]["analytics"] = topics.analytics;
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

void MQTTsetup() {
  client.setServer(mqttServer, mqttPort);
  client.setCallback(callback);
}

void reconnect_mqtt() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Create a random client ID
    String clientId = "ESP8266Client-";
    clientId += String(random(0xffff), HEX);
    // Attempt to connect
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
      // ... and resubscribe
      // client.subscribe(config.topics.manager);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
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
  if (currentMillis - previousTempSent >= config.time_steps.t_s[0] * 1000) {
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
  if (currentMillis - previousHumSent >= config.time_steps.t_s[1] * 1000) {
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
  MQTTsetup();
  // Starting the REST web server
  server.on("/rest/get_measure/Temperature", HTTP_GET, handle_getTemp);
  server.on("/rest/get_measure/Humidity", HTTP_GET, handle_getHum);
  server.onNotFound(handle_NotFound); 
  server.begin();
}

void loop() {
  if (!client.connected()) {
    reconnect_mqtt();
  }
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
