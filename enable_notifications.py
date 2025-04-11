# -*- coding: utf-8 -*-
"""
Notifications
-------------

Python script to interact with an Arduino Nano 33 IoT:
- Read IMU data from the `imuCharacteristic`.
- Send motor control commands to the `commandCharacteristic`.

Updated to match Arduino functionality by Brian Mmari.
"""

import argparse
import asyncio
import logging
from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic

logger = logging.getLogger(__name__)


def notification_handler(characteristic: BleakGATTCharacteristic, data: bytearray):
    """Handle and print BLE notifications for IMU data."""
    try:
        # Decode the bytearray into a UTF-8 string
        decoded_data = data.decode("utf-8")

        # Split the data into individual samples (assuming ';' separates samples)
        samples = decoded_data.strip(";").split(";")

        # Print each sample with a label
        for i, sample in enumerate(samples, start=1):
            print(f"Sample {i}: {sample}")
    except Exception as e:
        logger.error(f"Error decoding data: {e}")


async def main(device_name: str, imu_characteristic: str):
    """Connect to the BLE device, read notifications, and send commands."""
    logger.info("Scanning for device...")
    device = await BleakScanner.find_device_by_name(device_name)

    if not device:
        logger.error(f"Device '{device_name}' not found.")
        return

    async with BleakClient(device) as client:
        logger.info("Connected to device.")

        # Start notifications for IMU data
        await client.start_notify(imu_characteristic, notification_handler)

        try:
            while True:
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            logger.info("Notification listening cancelled.")
        finally:
            await client.stop_notify(imu_characteristic)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--name",
        metavar="<name>",
        help="The name of the Bluetooth device to connect to",
        required=True,
    )

    parser.add_argument(
        "imu_characteristic",
        metavar="<imu uuid>",
        help="UUID of the IMU data characteristic for notifications",
    )

    # parser.add_argument(
    #     "command_characteristic",
    #     metavar="<command uuid>",
    #     help="UUID of the command characteristic for writing commands",
    # )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Sets the log level to debug",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
    )

    asyncio.run(main(args.name, args.imu_characteristic))
