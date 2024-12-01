#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Keypad.h>

// RFID Pin configuration
#define SS_PIN 5
#define RST_PIN 4
MFRC522 mfrc522(SS_PIN, RST_PIN);

// Solenoid Pin
#define SOLENOID_PIN 15

// WiFi credentials
const char* ssid = "praktekan104";
const char* password = "tidakpakai";

// Server endpoints
const char* rfidServer = "https://projek-akhir-eosin.vercel.app/rfid";
const char* pinServer = "https://projek-akhir-eosin.vercel.app/pin_access";

// Keypad configuration
const byte ROW_NUM = 4;
const byte COLUMN_NUM = 4;
char keys[ROW_NUM][COLUMN_NUM] = {
  {'1', '2', '3', 'A'},
  {'4', '5', '6', 'B'},
  {'7', '8', '9', 'C'},
  {'*', '0', '#', 'D'}
};
byte pin_rows[ROW_NUM] = {13, 12, 14, 27};
byte pin_column[COLUMN_NUM] = {26, 25, 33, 32};
Keypad keypad = Keypad(makeKeymap(keys), pin_rows, pin_column, ROW_NUM, COLUMN_NUM);

// Entered PIN
String enteredPIN = "";
bool lockerOccupied = false; // State of the locker

void setup() {
  Serial.begin(115200);
  SPI.begin();
  mfrc522.PCD_Init();
  pinMode(SOLENOID_PIN, OUTPUT);
  digitalWrite(SOLENOID_PIN, LOW);

  // WiFi setup
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi");
  Serial.println("Ready for RFID or PIN input.");
}

void loop() {
  char key = keypad.getKey();
  if (key) {
    handleKeypadInput(key);
  }

  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    handleRFID();
  }
}

// Handle keypad input
void handleKeypadInput(char key) {
  if (key == '#') {
    submitPIN();
  } else if (key == '*') {
    enteredPIN = "";
    Serial.println("PIN cleared.");
  } else if (key == 'A') { // 'A' key acts as the release button
    handleReleaseButton();
  } else if (key >= '0' && key <= '9') {
    enteredPIN += key;
    Serial.println("Entered PIN: " + enteredPIN);
  }
}

// Submit PIN to server
void submitPIN() {
  if (enteredPIN.length() == 6) {
    Serial.println("Submitting PIN to server...");
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(pinServer);
      http.addHeader("Content-Type", "application/x-www-form-urlencoded");

      String postData = "pin=" + enteredPIN;
      int httpResponseCode = http.POST(postData);

      if (httpResponseCode == 200) {
        String response = http.getString();
        Serial.println("Server Response: " + response);
        if (!lockerOccupied) {
          openLocker();
        } else {
          Serial.println("Locker already in use.");
        }
      } else {
        Serial.println("Access denied or server error.");
      }
      http.end();
    } else {
      Serial.println("WiFi not connected.");
    }
    enteredPIN = "";
  } else {
    Serial.println("Incomplete PIN entry.");
  }
}

// Handle RFID input
void handleRFID() {
  String rfidTag = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    rfidTag += String(mfrc522.uid.uidByte[i], HEX);
  }
  Serial.println("RFID Tag: " + rfidTag);

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(rfidServer);
    http.addHeader("Content-Type", "application/x-www-form-urlencoded");

    String postData = "rfid=" + rfidTag;
    int httpResponseCode = http.POST(postData);

    if (httpResponseCode == 200) {
      String response = http.getString();
      Serial.println("Server Response: " + response);
      if (!lockerOccupied) {
        openLocker();
      } else {
        Serial.println("Locker already in use.");
      }
    } else {
      Serial.println("Access denied or server error.");
    }
    http.end();
  } else {
    Serial.println("WiFi not connected.");
  }
}

// Open locker
void openLocker() {
  lockerOccupied = true;
  digitalWrite(SOLENOID_PIN, HIGH);
  Serial.println("Locker opened. Solenoid ON.");
}

// Handle release action
void handleReleaseButton() {
  if (lockerOccupied) {
    lockerOccupied = false;
    digitalWrite(SOLENOID_PIN, LOW);
    Serial.println("Locker closed. Solenoid OFF.");
  } else {
    Serial.println("Locker is already closed.");
  }
}