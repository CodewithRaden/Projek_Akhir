#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>

const char* ssid = "RadenLt2";           // Your WiFi SSID
const char* password = "onlyraden123"; // Your WiFi password
const char* serverName = "https://projek-akhir-eosin.vercel.app/rfid";  // Flask server URL

void setup() {
  Serial.begin(115200);

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi");
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    http.begin(serverName);  // Initialize connection to server
    http.addHeader("Content-Type", "application/x-www-form-urlencoded");

    String rfidTag = "1234567890";  // Hardcoded RFID value for testing
    String postData = "rfid=" + rfidTag;

    // Send POST request
    int httpResponseCode = http.POST(postData);

    // Handle response
    if (httpResponseCode > 0) {
      Serial.println("HTTP Response Code: " + String(httpResponseCode));
      String response = http.getString();
      Serial.println("Server Response: " + response);
    } else {
      Serial.println("Error in sending POST: " + String(httpResponseCode));
    }

    http.end();  // Close connection
  } else {
    Serial.println("WiFi not connected");
  }

  delay(5000);  // Wait before sending the next request
}
