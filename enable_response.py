import argparse
import asyncio
import threading
from multiprocessing import Queue, Process
from bleak import BleakClient, BleakScanner
from queue import Empty  # Import Empty exception

from devel_notifications import main as notifications_main
import queue  # Import the queue module

# async def process_queue_and_write(client: BleakClient, queue: Queue, write_characteristic: str):
#     """Process motor commands from the queue and send them via BLE."""
#     while True:
#         try:
#             message = queue.get_nowait()  # Use get_nowait() to prevent blocking
#             if validate_motor_command(message):
#                 print(f"Sending motor command: {message}")
#                 await client.write_gatt_char(write_characteristic, message.encode("utf-8"))
#             else:
#                 print(f"Invalid command format: {message}")
#         except Empty:  # Handle the case when the queue is empty
#             pass
#         except Exception as e:
#             print(f"Error in writing to BLE device: {e}")
#         finally:
#             await asyncio.sleep(0.05)  # Reduce delay to speed up motor command handling

async def process_queue_and_write(client: BleakClient, queue: Queue, write_characteristic: str):
    """Process motor commands from the queue and send them via BLE."""
    while True:
        try:
            message = queue.get_nowait()  # Use get_nowait() to prevent blocking

            # Ensure the BLE device is connected
            if not client.is_connected:
                print("BLE device is not connected. Waiting for reconnection...")
                await asyncio.sleep(1)
                continue  # Skip this iteration and retry later

            # Ensure services are discovered before writing
            if not client.services:
                print("BLE services not discovered yet. Waiting...")
                await asyncio.sleep(1)
                continue  

            if validate_motor_command(message):
                print(f"Sending motor command: {message}")
                await client.write_gatt_char(write_characteristic, message.encode("utf-8"))
            else:
                print(f"Invalid command format: {message}")

        except Empty:  # Handle the case when the queue is empty
            pass
        except Exception as e:
            print(f"Error in writing to BLE device: {e}")
            await asyncio.sleep(1)  # Wait and retry in case of transient errors
        finally:
            await asyncio.sleep(0.05)  # Reduce delay to speed up motor command handling

async def imu_callback(sender, data):
    """Callback function to handle IMU data from BLE notifications."""
    imu_data = data.decode("utf-8")
    print(f"IMU Data: {imu_data}")

async def read_imu_data(client: BleakClient, notify_characteristic: str):
    """Subscribe to IMU notifications instead of polling."""
    await client.start_notify(notify_characteristic, imu_callback)
    while True:
        await asyncio.sleep(1)  # Keeps the coroutine alive

# async def main(queue: Queue, device_name: str, notify_characteristic: str, write_characteristic: str):
#     """Find the BLE device, connect to it, and manage IMU data and motor commands."""
#     print("Scanning for device...")
#     device = await BleakScanner.find_device_by_name(device_name)

#     if not device:
#         print(f"Device '{device_name}' not found.")
#         return

#     async with BleakClient(device) as client:
#         print(f"Connected to {device_name}.")
#         await asyncio.gather(
#             read_imu_data(client, notify_characteristic),
#             process_queue_and_write(client, queue, write_characteristic)
#         )

async def main(queue: Queue, device_name: str, notify_characteristic: str, write_characteristic: str):
    print("Scanning for device...")
    device = await BleakScanner.find_device_by_name(device_name)
    if not device:
        print(f"Device '{device_name}' not found.")
        return

    async with BleakClient(device) as client:
        print(f"Connected to {device_name}.")
        
        # Start IMU and Motor tasks separately
        imu_task = asyncio.create_task(read_imu_data(client, notify_characteristic))
        motor_task = asyncio.create_task(process_queue_and_write(client, queue, write_characteristic))
        
        # Run both concurrently
        await asyncio.gather(imu_task, motor_task)


def run_notifications(name, address, notify_characteristic, write_characteristic, use_bdaddr, queue):
    """Run the BLE notifications function in a separate process."""
    asyncio.run(notifications_main(name, address, notify_characteristic, write_characteristic, use_bdaddr, queue))

def user_input_thread(queue):
    """Read user input for motor commands and add valid ones to the queue."""
    while True:
        command = input("Enter motor command (0, 2, 3, or halfPeriod_leftRatio_rightRatio): ").strip()
        if validate_motor_command(command):
            queue.put(command)
        else:
            print("Invalid command. Expected format: 0, 2, 3, or halfPeriod_leftRatio_rightRatio (e.g., 50_1_1).")

def validate_motor_command(command):
    """Validate command format for single values (0, 2, 3) or the old motor control format."""
    if command in {"0", "2", "3"}:  # Accepts single number commands
        return True
    parts = command.split("_")
    return len(parts) == 3 and all(part.isdigit() for part in parts)  # Accepts "halfPeriod_LeftDelay_RightDelay" format

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="Name of the BLE device")
    parser.add_argument("--address", help="Address of the BLE device")
    parser.add_argument("notify_characteristic", help="UUID of the notification characteristic (IMU data)")
    parser.add_argument("write_characteristic", help="UUID of the write characteristic (motor commands)")
    parser.add_argument("--macos-use-bdaddr", action="store_true", help="Use Bluetooth address instead of UUID on macOS")
    args = parser.parse_args()

    queue = Queue()

    # Start a separate thread for user input
    input_thread = threading.Thread(target=user_input_thread, args=(queue,), daemon=True)
    input_thread.start()

    # Start notifications process
    notification_process = Process(
        target=run_notifications,
        args=(args.name, args.address, args.notify_characteristic, args.write_characteristic, args.macos_use_bdaddr, queue)
    )
    notification_process.start()

    # Run the main BLE handling loop
    asyncio.run(main(queue, args.name, args.notify_characteristic, args.write_characteristic))

    # Ensure the notification process stops on exit
    notification_process.join()

