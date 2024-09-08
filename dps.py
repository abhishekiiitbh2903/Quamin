import hmac
import hashlib
import base64
import json
import os
from azure.iot.device import ProvisioningDeviceClient, IoTHubDeviceClient, Message
from azure.iot.hub import IoTHubRegistryManager
from dotenv import load_dotenv

load_dotenv()

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

    def check_device_registration(self, device_id):
        try:
            registry_manager = IoTHubRegistryManager(self.iot_hub_connection_string)
            device = registry_manager.get_device(device_id)
            if device is not None:
                print(f"Device {device_id} is already registered.")
                # Attempt to fetch the connection string if available
                connection_string = self.iot_hub_connection_string_template.get(device_id, None)
                if connection_string:
                    print(f"Connection String for {device_id}: {connection_string}")
                    return True
                else:
                    print(f"Connection string is not set for {device_id}.")
                    return False
            else:
                return False
        except Exception as e:
            print(f"Error checking device registration: {e}")
            return False

class MoistureSensorManager:
    def __init__(self):
        self.device = MoistureSensorDevice()
        self.devices = ["moistureSensor1", "moistureSensor2", "moistureSensor3", "moistureSensor4", "moistureSensor5"]

    def select_device(self):
        for idx, device in enumerate(self.devices, 1):
            print(f"{idx}. {device}")
        choice = int(input("Select the moisture sensor you want to connect (1-5): "))
        return self.devices[choice - 1]

    def run(self):
        selected_device = self.select_device()
        print(f"Selected Device: {selected_device}")
        derived_device_key = self.device.compute_derived_symmetric_key(selected_device)
        print(f"Derived Symmetric Key: {derived_device_key}")

        if not self.device.check_device_registration(selected_device):
            try:
                hub_name, device_id = self.device.register_device(selected_device, derived_device_key)
                print(f"Hub Name: {hub_name}, Device ID: {device_id}")
                connection_string = self.device.get_connection_string(hub_name, device_id)
                print(f"Connection String for {selected_device}: {connection_string}")
                self.device.iot_hub_connection_string_template[selected_device] = connection_string
                print(f"Updated Connection Strings: {self.device.iot_hub_connection_string_template}")
            except Exception as e:
                print(f"Error during DPS registration: {e}")
                return
        else:
            connection_string = self.device.iot_hub_connection_string_template.get(selected_device, None)
            if connection_string is None:
                print("Connection string is not available for already registered device.")
                return
            else:
                print(f"Connection String for {selected_device}: {connection_string}")

        telemetry_data = {
            "temperature": 22.0,
            "humidity": 55,
            "sensor_name": selected_device
        }

        try:
            connection_string = self.device.iot_hub_connection_string_template[selected_device]
            if connection_string:
                print(f"Sending telemetry to {selected_device} with connection string: {connection_string}")
                self.device.send_telemetry(connection_string, telemetry_data)
            else:
                print("Connection string is not available.")
        except Exception as e:
            print(f"Failed to send telemetry: {e}")

if __name__ == "__main__":
    manager = MoistureSensorManager()
    manager.run()
