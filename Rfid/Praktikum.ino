#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <ESP8266WebServer.h>
#include "DHT.h"

#define DHTTYPE DHT11
#define LED D4
const int DHTPin = D2;
DHT dht(DHTPin, DHTTYPE);

const char* ssid = "Raden";
const char* password = "papamamaandus";

ESP8266WebServer server(80);

const char MAIN_page[] PROGMEM = R"=====( 
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            background-color: #f0f0f0;
            font-family: 'Arial', sans-serif;
            color: #333;
            text-align: center;
            margin: 0;
            padding: 0;
        }
        .header-image {
            width: 200px;
            height: auto;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            margin-top: 20px;
        }
        h1 {
            color: #2c3e50;
            font-size: 36px;
            margin-bottom: 10px;
        }
        h3 {
            color: #16a085;
            font-size: 24px;
        }
        p {
            font-size: 18px;
            color: #34495e;
            line-height: 1.5;
        }
        a {
            font-size: 16px;
            color: #2980b9;
            text-decoration: none;
            padding: 10px 20px;
            background-color: #ecf0f1;
            border-radius: 5px;
            margin: 5px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            display: inline-block;
        }
        a:hover {
            background-color: #3498db;
            color: #fff;
        }
        hr {
            width: 80%;
            border: 0;
            height: 1px;
            background-color: #bdc3c7;
            margin: 20px 0;
        }
        span {
            font-size: 20px;
            color: #e74c3c;
        }
    </style>
</head>
<body>
<center>
    <h1>Website Kontrol LED & Monitoring Suhu</h1><br>
    <img src="https://i.pinimg.com/736x/a7/9b/a2/a79ba2bb1b4cc35cdaf2a30b921ad128.jpg" alt="Logo" class="header-image"><br>
    <h3>Made By Raden Muhammad Fadil Azhar</h3><br>
    <p>Halo, perkenalkan saya Raden Muhammad Fadil Azhar dari kelas Blynk MSIB Cycle 7 Indobot Academy. Saat ini, saya sedang praktikum dengan Wemos D1 Mini untuk membuat Web Server ini.</p><br>
    <h4>LED Kontrol</h4><br>
    <a href="ledOn">LED ON</a>
    <a href="ledOff">LED OFF</a>
    <a href="toggleBlink">LED BLINK</a>
    <hr>
    <h4>Monitoring Suhu</h4><br>
    Suhu dalam Celcius: <span id="tempC"></span> *C <br>
    Suhu dalam Fahrenheit: <span id="tempF"></span> *F <br>
    Kelembaban: <span id="humidity"></span> %<br>
    <br>
    <a href="https://indobot.co.id">Raden</a>
</center>
<script>
setInterval(function() {
    fetch("/getSensorData").then(response => response.json()).then(data => {
        document.getElementById("tempC").innerHTML = data.tempC;
        document.getElementById("tempF").innerHTML = data.tempF;
        document.getElementById("humidity").innerHTML = data.humidity;
    });
}, 2000);
</script>
</body>
</html>
)=====";

bool blinkState = false;
bool blinking = false;
unsigned long previousMillis = 0;
const long interval = 1000;

void handleRoot() {
    String s = MAIN_page;
    server.send(200, "text/html", s);
}

void handleLEDon() {
    digitalWrite(LED, HIGH);
    blinking = false;
    server.send(200, "text/html", "LED is ON");
}

void handleLEDoff() {
    digitalWrite(LED, LOW);
    blinking = false;
    server.send(200, "text/html", "LED is OFF");
}

void handleToggleBlink() {
    blinking = !blinking;
    server.send(200, "text/html", blinking ? "LED is BLINKING" : "LED STOPPED BLINKING");
}

void handleSensorData() {
    float h = dht.readHumidity();
    float t = dht.readTemperature();
    float f = dht.readTemperature(true);

    if (isnan(h) || isnan(t) || isnan(f)) {
        server.send(500, "application/json", "{\"error\":\"Failed to read from DHT sensor!\"}");
        return;
    }

    String json = "{\"tempC\":";
    json += String(t);
    json += ",\"tempF\":";
    json += String(f);
    json += ",\"humidity\":";
    json += String(h);
    json += "}";

    server.send(200, "application/json", json);
}

void setup(void) {
    Serial.begin(115200);
    dht.begin();

    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("");
    Serial.print("Connected to ");
    Serial.println(ssid);
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());

    pinMode(LED, OUTPUT);
    digitalWrite(LED, LOW);

    server.on("/", handleRoot);
    server.on("/ledOn", handleLEDon);
    server.on("/ledOff", handleLEDoff);
    server.on("/toggleBlink", handleToggleBlink);
    server.on("/getSensorData", handleSensorData);

    server.begin();
    Serial.println("HTTP server started");
}

void loop(void) {
    server.handleClient();

    unsigned long currentMillis = millis();
    if (blinking && currentMillis - previousMillis >= interval) {
        previousMillis = currentMillis;
        blinkState = !blinkState;
        digitalWrite(LED, blinkState ? HIGH : LOW);
    }
}
