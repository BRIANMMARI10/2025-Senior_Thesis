import asyncio
from bleak import BleakScanner, BleakClient
import matplotlib.pyplot as plt
from collections import deque
import matplotlib.animation as animation

# === BLE Setup ===
DEVICE_NAME = "Nano33IMU"
CHAR_UUID = "2A58"
MAX_LEN = 200

# === Buffers ===
gz_vals = deque([0]*MAX_LEN, maxlen=MAX_LEN)
smoothed_vals = deque([0]*MAX_LEN, maxlen=MAX_LEN)
error_vals = deque([0]*MAX_LEN, maxlen=MAX_LEN)
integral_vals = deque([0]*MAX_LEN, maxlen=MAX_LEN)
derivative_vals = deque([0]*MAX_LEN, maxlen=MAX_LEN)

# === Plot Setup ===
fig, ax = plt.subplots()
line_gz, = ax.plot([], [], label="gz")
line_smoothed, = ax.plot([], [], label="smoothed_gz")
line_error, = ax.plot([], [], label="error")
line_integral, = ax.plot([], [], label="integral")
line_derivative, = ax.plot([], [], label="derivative")

ax.set_ylim(-5, 5)
ax.set_xlim(0, MAX_LEN)
ax.set_title("Real-Time PID Over BLE")
ax.legend()
ax.grid(True)

# === Callback ===
def handle_notify(sender, data):
    try:
        line = data.decode("utf-8").strip()
        print(f"Received: {line}")  # 💥 Add this
        parts = [float(x) for x in line.split(",")]
        if len(parts) != 5:
            print(f"Ignoring malformed data: {line}")
            return

        gz, smoothed, error, integral, derivative = parts
        gz_vals.append(gz)
        smoothed_vals.append(smoothed)
        error_vals.append(error)
        integral_vals.append(integral)
        derivative_vals.append(derivative)

    except Exception as e:
        print(f"Error decoding: {data} — {e}")

# === Live Plot Update ===
def update(frame):
    line_gz.set_data(range(len(gz_vals)), gz_vals)
    line_smoothed.set_data(range(len(smoothed_vals)), smoothed_vals)
    line_error.set_data(range(len(error_vals)), error_vals)
    line_integral.set_data(range(len(integral_vals)), integral_vals)
    line_derivative.set_data(range(len(derivative_vals)), derivative_vals)
    return line_gz, line_smoothed, line_error, line_integral, line_derivative

ani = animation.FuncAnimation(fig, update, interval=100, save_count=MAX_LEN)

# === Main BLE Handler ===
async def main():
    print("Scanning for device...")
    devices = await BleakScanner.discover(timeout=5.0)
    for d in devices:
        print(f"- {d.name} [{d.address}]")

    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)
    if not device:
        print(f"❌ Device '{DEVICE_NAME}' not found.")
        return

    print(f"✅ Found device: {device.name} @ {device.address}")

    async with BleakClient(device) as client:
        print(f"🔗 Connected to {DEVICE_NAME}")
        await client.start_notify(CHAR_UUID, handle_notify)

        # assign ani here
        ani = animation.FuncAnimation(fig, update, interval=100, save_count=MAX_LEN)
        print("📡 Subscribed to notifications. Launching plot...")
        plt.show()  # Blocking, but animation stays alive

if __name__ == "__main__":
    asyncio.run(main())
