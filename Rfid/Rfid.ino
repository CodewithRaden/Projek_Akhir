#include <SPI.h>
#include <MFRC522.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>

#define RST_PIN D3  // Reset pin
#define SS_PIN D4   // SDA pin for RFID
#define LED_PIN D1  // LED pin (uses D1)

MFRC522 mfrc522(SS_PIN, RST_PIN);  // Create MFRC522 instance

const char* ssid = "Raden";           // WiFi name
const char* password = "papamamaandus";   // WiFi password
const char* serverName = "https://projek-akhir-eosin.vercel.app/rfid";  // Server address

WiFiClientSecure client;  // Use WiFiClientSecure for HTTPS

void setup() {
  Serial.begin(115200);
  SPI.begin();
  mfrc522.PCD_Init();

  // Configure LED pin
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);  // LED off (locker locked)

  // Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi");

  // Configure client for SSL/TLS
  client.setInsecure();  // WARNING: For testing only; accepts all certificates
}

void loop() {
  if (!mfrc522.PICC_IsNewCardPresent()) {
    return;
  }

  if (!mfrc522.PICC_ReadCardSerial()) {
    return;
  }

  // Get the RFID tag
  String rfidTag = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    rfidTag += String(mfrc522.uid.uidByte[i], HEX);
  }

  Serial.println("RFID Tag: " + rfidTag);

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    // Debug server connection
    Serial.println("Attempting to connect to server...");
    http.setTimeout(15000);  // Increase timeout to 15 seconds
    http.begin(client, serverName);  // Use WiFiClientSecure for HTTPS

    // Add headers
    http.addHeader("Content-Type", "application/x-www-form-urlencoded");

    String postData = "rfid=" + rfidTag;
    int httpResponseCode = http.POST(postData);

    if (httpResponseCode > 0) {
      // Successful HTTP request
      String response = http.getString();
      Serial.println("HTTP Response Code: " + String(httpResponseCode));
      Serial.println("Server Response: " + response);

      if (httpResponseCode == 200) {
        Serial.println("Access Granted!");
        digitalWrite(LED_PIN, HIGH);  // Turn on LED (locker open)
        delay(5000);  // Simulate locker open for 5 seconds
        digitalWrite(LED_PIN, LOW);   // Turn off LED (locker locked)
      } else {
        Serial.println("Access Denied.");
        digitalWrite(LED_PIN, LOW);   // Keep LED off (locker locked)
      }
    } else {
      // Failed HTTP request
      Serial.println("Error in sending POST: " + String(httpResponseCode));
      Serial.println("Check your server or network connection.");
    }

    http.end();
  } else {
    Serial.println("WiFi not connected.");
  }

  delay(2000);
}
