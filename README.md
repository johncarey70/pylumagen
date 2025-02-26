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
After installation, you can use the `lumagen-cli` command-line tool.

#### **Step 1: Run the CLI**
Open a terminal and enter:

```sh
lumagen-cli --log-level DEBUG --exit-wait-timer 5
```

#### **Step 2: Enter a Lumagen Command**
Once the prompt appears, **type the following command exactly as shown**:

```sh
ZQS01
```

**Note:** This sends the **ZQS01** command to the Lumagen device.
**Tip** *(Replace `ZQS01` with another valid Lumagen API command if needed.)*


---

### Python API Usage
You can also send commands directly using the Python API:

```python
#!/usr/bin/env python3

import asyncio
from lumagen.device_manager import DeviceManager

async def main():
    device = DeviceManager(connection_type="ip")
    await device.open(host="192.168.15.71", port=4999)

    # Send a specific command
    await device.send_command("ZQS01")  # Change "ZQS01" if needed

    await device.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Home Assistant Integration
**pylumagen** was mainly designed to support the Lumagen Home Assistant component.

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
