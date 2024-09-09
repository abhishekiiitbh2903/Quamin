import hmac
import hashlib
import base64
import json
import os
import threading
from typing import List, Dict, Optional
from azure.iot.device import ProvisioningDeviceClient, IoTHubDeviceClient, Message
from azure.iot.hub import IoTHubRegistryManager
from dotenv import load_dotenv

load_dotenv()

class MoistureSensorDevice:
    def __init__(self) -> None:
        self.provisioning_host: str = os.getenv("PROVISIONING_HOST")
        self.id_scope: str = os.getenv("ID_SCOPE")
        self.group_enrollment_primary_key: str = os.getenv("GROUP_ENROLLMENT_PRIMARY_KEY")
        self.iot_hub_connection_string: str = os.getenv("IOT_HUB_CONNECTION_STRING")
        self.iot_hub_connection_string_template: Dict[str, Optional[str]] = {
            "moistureSensor1": None,
            "moistureSensor2": None,
            "moistureSensor3": None,
            "moistureSensor4": None,
            "moistureSensor5": None
        }

    def compute_derived_symmetric_key(self, device_id: str) -> str:
        message = device_id.encode('utf-8')
        key = base64.b64decode(self.group_enrollment_primary_key.encode('utf-8'))
        signature = hmac.new(key, message, digestmod=hashlib.sha256).digest()
        return base64.b64encode(signature).decode("utf-8")

    def register_device(self, registration_id: str, symmetric_key: str) -> tuple[str, str]:
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

    def get_connection_string(self, hub_name: str, device_id: str) -> str:
        return f"HostName={hub_name};DeviceId={device_id};SharedAccessKey={self.compute_derived_symmetric_key(device_id)}"

    def send_telemetry(self, connection_string: str, telemetry_data: Dict[str, str]) -> None:
        client = IoTHubDeviceClient.create_from_connection_string(connection_string)
        try:
            client.connect()
            telemetry_message = Message(json.dumps(telemetry_data))
            client.send_message(telemetry_message)
        finally:
            client.disconnect()

    def check_device_registration(self, device_id: str) -> bool:
        try:
            registry_manager = IoTHubRegistryManager(self.iot_hub_connection_string)
            device = registry_manager.get_device(device_id)
            if device is not None:
                print(f"Device {device_id} is already registered.")
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
    def __init__(self) -> None:
        self.device = MoistureSensorDevice()
        self.devices: List[str] = ["moistureSensor1", "moistureSensor2", "moistureSensor3", "moistureSensor4", "moistureSensor5"]

    def select_devices(self) -> List[str]:
        print("Available Moisture Sensors:")
        for idx, device in enumerate(self.devices, 1):
            print(f"{idx}. {device}")
        choices = input("Select the moisture sensors you want to connect (e.g., 1,3,5): ")
        selected_indices = [int(choice.strip()) - 1 for choice in choices.split(",")]
        return [self.devices[idx] for idx in selected_indices]

    def send_telemetry_to_device(self, selected_device: str) -> None:
        derived_device_key = self.device.compute_derived_symmetric_key(selected_device)
        print(f"Derived Symmetric Key for {selected_device}: {derived_device_key}")

        connection_string = self.device.iot_hub_connection_string_template.get(selected_device, None)

        if not self.device.check_device_registration(selected_device):
            try:
                hub_name, device_id = self.device.register_device(selected_device, derived_device_key)
                print(f"Hub Name: {hub_name}, Device ID: {device_id}")
                connection_string = self.device.get_connection_string(hub_name, device_id)
                print(f"Connection String for {selected_device}: {connection_string}")
                self.device.iot_hub_connection_string_template[selected_device] = connection_string
            except Exception as e:
                print(f"Error during DPS registration for {selected_device}: {e}")
                return
        else:
            if connection_string is None:
                print(f"Connection string is not available for already registered {selected_device}.")
                return

        telemetry_data: Dict[str, str] = {
            "temperature": "22.0",
            "humidity": "55",
            "sensor_name": selected_device
        }

        try:
            if connection_string:
                print(f"Sending telemetry to {selected_device} with connection string: {connection_string}")
                self.device.send_telemetry(connection_string, telemetry_data)
                print(f"Telemetry data sent to {selected_device}.")
            else:
                print("Connection string is not available.")
        except Exception as e:
            print(f"Failed to send telemetry for {selected_device}: {e}")

    def run(self) -> None:
        selected_devices = self.select_devices()
        threads: List[threading.Thread] = []

        for device in selected_devices:
            print(f"Processing device: {device}")
            thread = threading.Thread(target=self.send_telemetry_to_device, args=(device,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

if __name__ == "__main__":
    manager = MoistureSensorManager()
    manager.run()
