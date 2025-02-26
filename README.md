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
#!/usr/bin/env python3

import asyncio
import logging
from lumagen.device_manager import DeviceManager

async def main():
    device = DeviceManager(connection_type="ip")
    await device.open(host="192.168.15.71", port=4999)
    await asyncio.sleep(1)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    await device.send_command("ZQS01")
    await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
```

## Home Assistant Integration
**pylumagen** is designed to support the Lumagen Home Assistant component.

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

