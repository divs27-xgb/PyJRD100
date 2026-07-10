#define RXD2 16
#define TXD2 17

void setup() {
  Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, RXD2, TXD2);
}

void loop() {
  //Send
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();

    if (line.length() > 0) {
      uint8_t bytes[64];
      int count = 0;

      int i = 0;
      while (i < line.length() && count < 64) {
        while (i < line.length() && line[i] == ' ') i++;
        if (i + 1 >= line.length()) break;

        String pair = line.substring(i, i + 2);
        bytes[count] = (uint8_t) strtol(pair.c_str(), NULL, 16);
        count++;
        i += 2;
      }

      Serial2.write(bytes, count);
    }
  }
  //Receiver
  while (Serial2.available()) {
    Serial.write(Serial2.read());
  }
}