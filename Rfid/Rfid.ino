#include <SPI.h>
#include <MFRC522.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>

#define RST_PIN D3  // Reset pin
#define SS_PIN D4   // SDA pin untuk RFID
#define LED_PIN D1  // Pin untuk LED (menggunakan D1)

MFRC522 mfrc522(SS_PIN, RST_PIN);  // Create MFRC522 instance

const char* ssid = "Raden";           // Nama WiFi
const char* password = "papamamaandus";   // Password WiFi
const char* serverName = "http://192.168.1.6:5000/rfid";  // IP address server Flask

WiFiClient client;  // WiFiClient

void setup() {
  Serial.begin(115200);
  SPI.begin();
  mfrc522.PCD_Init();

  // Set LED pin sebagai output
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);  // Awal LED dalam keadaan mati (loker terkunci)

  // Koneksi ke WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("Connected to WiFi");
}

void loop() {
  if (!mfrc522.PICC_IsNewCardPresent()) {
    return;
  }
  
  if (!mfrc522.PICC_ReadCardSerial()) {
    return;
  }

  String rfidTag = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    rfidTag += String(mfrc522.uid.uidByte[i], HEX);
  }

  Serial.println("RFID Tag: " + rfidTag);

  if(WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(client, serverName);  // Gunakan WiFiClient dalam begin()

    http.addHeader("Content-Type", "application/x-www-form-urlencoded");

    String postData = "rfid=" + rfidTag;
    int httpResponseCode = http.POST(postData);

    if(httpResponseCode > 0) {
      String response = http.getString();
      Serial.println(httpResponseCode);
      Serial.println(response);

      if (httpResponseCode == 200) {
        Serial.println("Access Granted!");
        digitalWrite(LED_PIN, HIGH);  // Nyalakan LED (loker terbuka)
        delay(5000);  // Simulasikan loker terbuka selama 5 detik
        digitalWrite(LED_PIN, LOW);   // Matikan LED kembali (loker terkunci)
      } else {
        Serial.println("Access Denied.");
        digitalWrite(LED_PIN, LOW);   // Tetap matikan LED (loker terkunci)
      }
    } else {
      Serial.println("Error in sending POST");
    }
    http.end();
  }

  delay(2000);
}
