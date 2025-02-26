# pylumagen

## Overview
**pylumagen** is a Python package for integrating and controlling Lumagen video processors, particularly in support of a **Home Assistant Lumagen Integration**. It also includes a command-line tool, `lumagen-cli`, for direct interaction with Lumagen devices.

## Features
- Communicate with Lumagen devices via serial or network
- Send custom commands and receive responses
- Automate video processing tasks
- Includes `lumagen-cli` for direct command execution
- Home Assistant integration support

## Installation
To install **pylumagen**, you can use:

```sh
pip install pylumagen
```

Or clone and install from source:

```sh
git clone https://github.com/johncarey70/pylumagen.git
cd pylumagen
pip install .
```

## Usage
### Lumagen CLI
After installation, you can use the `lumagen-cli` command-line tool:

```sh
lumagen-cli --help
```

Example usage:
```sh
lumagen-cli --log-level DEBUG --exit-wait-timer 5
```

### Python API
You can also use **pylumagen** as a Python module:

```python
from lumagen.device_manager import DeviceManager

async def main():
    device = DeviceManager(connection_type="ip")
    await device.open(host="192.168.1.100", port=23)
    await device.send_command("ZQI00")
    await device.close()
```

## Configuration
Ensure you have the correct configuration settings for your Lumagen device. Edit the `config.yaml` file to match your setup:

```yaml
lumagen:
  host: "192.168.1.100"
  port: 23
  serial_port: "/dev/ttyUSB0"
```

## Home Assistant Integration
**pylumagen** is designed to support integration with Home Assistant. Ensure you install this package before using the Lumagen Home Assistant component.

## Contributing
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature-name`).
3. Commit your changes (`git commit -m "Add new feature"`).
4. Push to the branch (`git push origin feature-name`).
5. Open a pull request.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.

## Contact
For any questions or issues, please open an issue on GitHub or contact the maintainer.

---
Happy coding! 🚀

