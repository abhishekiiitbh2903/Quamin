from azure.iot.device import IoTHubDeviceClient, Message

class IoTDevice:
    def __init__(self, connection_string):
        self.client = IoTHubDeviceClient.create_from_connection_string(connection_string)

    def connect(self):
        try:
            self.client.connect()
            print("Connected to IoT Hub.")
        except Exception as e:
            print(f"An error occurred while connecting: {e}")

    def disconnect(self):
        try:
            self.client.disconnect()
            print("Disconnected from IoT Hub.")
        except Exception as e:
            print(f"An error occurred while disconnecting: {e}")

    def send_telemetry(self, telemetry_data):
        try:
            telemetry_message = Message(str(telemetry_data))
            self.client.send_message(telemetry_message)
            print("Telemetry data sent successfully!")
        except Exception as e:
            print(f"An error occurred while sending telemetry data: {e}")

if __name__ == "__main__":
    CONNECTION_STRING = "HostName=AgricareIOT-moistureSensor.azure-devices.net;DeviceId=abhishek-device;SharedAccessKey=pH29816DNFqDB91sICxk0rJYu67xoB0lYAIoTFIV2qU="

    iot_device = IoTDevice(CONNECTION_STRING)

    telemetry_data = {
        "temperature": 23.5,
        "humidity": 60,
        "heart_rate": 72
    }

    iot_device.connect()
    iot_device.send_telemetry(telemetry_data)
    iot_device.disconnect()
