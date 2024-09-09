from flask import Flask, render_template, request
import time
import threading
from azure.iot.device import ProvisioningDeviceClient, IoTHubDeviceClient, Message
from azure.iot.hub import IoTHubRegistryManager
import os
import base64
import hmac
import hashlib
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Flask app initialization
app = Flask(__name__)

# MoistureSensorDevice class for Azure IoT DPS connection
class MoistureSensorDevice:
    def __init__(self):
        self.provisioning_host = os.getenv("PROVISIONING_HOST")
        self.id_scope = os.getenv("ID_SCOPE")
        self.group_enrollment_primary_key = os.getenv("GROUP_ENROLLMENT_PRIMARY_KEY")
        self.iot_hub_connection_string = os.getenv("IOT_HUB_CONNECTION_STRING")
        self.iot_hub_connection_string_template = {
            "moistureSensor1": None,
            "moistureSensor2": None,
            "moistureSensor3": None,
            "moistureSensor4": None,
            "moistureSensor5": None
        }

    def compute_derived_symmetric_key(self, device_id):
        message = device_id.encode('utf-8')
        key = base64.b64decode(self.group_enrollment_primary_key.encode('utf-8'))
        signature = hmac.new(key, message, digestmod=hashlib.sha256).digest()
        return base64.b64encode(signature).decode("utf-8")

    def register_device(self, registration_id, symmetric_key):
        client = ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=self.provisioning_host,
            registration_id=registration_id,
            id_scope=self.id_scope,
            symmetric_key=symmetric_key
        )
        registration_result = client.register()
        if registration_result.status == "assigned":
            return registration_result.registration_state.assigned_hub, registration_result.registration_state.device_id
        else:
            raise Exception(f"Device {registration_id} registration failed with status: {registration_result.status}")

    def get_connection_string(self, hub_name, device_id):
        return f"HostName={hub_name};DeviceId={device_id};SharedAccessKey={self.compute_derived_symmetric_key(device_id)}"

    def send_telemetry(self, connection_string, telemetry_data):
        client = IoTHubDeviceClient.create_from_connection_string(connection_string)
        try:
            client.connect()
            telemetry_message = Message(json.dumps(telemetry_data))
            client.send_message(telemetry_message)
        finally:
            client.disconnect()

# Initialize the MoistureSensorDevice class
device = MoistureSensorDevice()

# Simulate the connection of the sensor to DPS and send telemetry data
def connect_to_dps(sensor_name):
    try:
        # Compute the symmetric key for the selected device
        derived_device_key = device.compute_derived_symmetric_key(sensor_name)

        # Register the device with DPS if it is not already registered
        hub_name, device_id = device.register_device(sensor_name, derived_device_key)
        connection_string = device.get_connection_string(hub_name, device_id)

        # Send telemetry data to the IoT Hub
        telemetry_data = {
            "temperature": 22.0,
            "humidity": 55,
            "sensor_name": sensor_name
        }
        device.send_telemetry(connection_string, telemetry_data)

        return f"{sensor_name} successfully connected to DPS and telemetry sent."
    except Exception as e:
        return f"Error connecting {sensor_name} to DPS: {e}"

# Home route displaying the sensors and start buttons
@app.route('/')
def index():
    return render_template('index.html')

# Route handling the start button action
@app.route('/start', methods=['POST'])
def start_sensor():
    sensor_name = request.form.get('sensor')
    status = connect_to_dps(sensor_name)
    return render_template('result.html', sensor_name=sensor_name, status=status)

# Flask app entry point
if __name__ == '__main__':
    app.run(debug=True)
