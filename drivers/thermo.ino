#include <OneWire.h>
#include <DallasTemperature.h>

// Define sensor pins (analog pins used as digital I/O)
#define PIN_PLATFORM_LEFT 2
#define PIN_PLATFORM_RIGHT 3
#define PIN_AIR 4
#define PIN_BOX 5
#define PIN_BATTERY_LIGHT 6

// OneWire buses for each sensor
OneWire oneWireLeft(PIN_PLATFORM_LEFT);
OneWire oneWireRight(PIN_PLATFORM_RIGHT);
OneWire oneWireAir(PIN_AIR);
OneWire oneWireBox(PIN_BOX);
OneWire oneWireBattery(PIN_BATTERY_LIGHT);

// DallasTemperature sensor objects
DallasTemperature sensorLeft(&oneWireLeft);
DallasTemperature sensorRight(&oneWireRight);
DallasTemperature sensorAir(&oneWireAir);
DallasTemperature sensorBox(&oneWireBox);
DallasTemperature sensorBattery(&oneWireBattery);

void setup() {
  Serial.begin(9600);

  sensorLeft.begin();
  sensorRight.begin();
  sensorAir.begin();
  sensorBox.begin();
  sensorBattery.begin();
}

void loop() {
  sensorLeft.requestTemperatures();
  sensorRight.requestTemperatures();
  sensorAir.requestTemperatures();
  sensorBox.requestTemperatures();
  sensorBattery.requestTemperatures();

  float t_left = sensorLeft.getTempCByIndex(0);
  float t_right = sensorRight.getTempCByIndex(0);
  float t_air = sensorAir.getTempCByIndex(0);
  float t_box = sensorBox.getTempCByIndex(0);
  float t_batt = sensorBattery.getTempCByIndex(0);

  Serial.print(t_left);
  Serial.print(";");
  Serial.print(t_right);
  Serial.print(";");
  Serial.print(t_air);
  Serial.print(";");
  Serial.print(t_box);
  Serial.print(";");
  Serial.print(t_batt);
  Serial.print('\n');
  // No need for delay since reading the temperatures takes a few seconds
}