"""Minimal example for launching Annie Local programmatically."""

import uvicorn

from annie.core.config import AnnieConfig
from annie.server import create_app

config = AnnieConfig(model="llama3.2")
app = create_app(config)


if __name__ == "__main__":
    uvicorn.run(app, host=config.host, port=config.port)
