# server.py
import os
import logging

from quart import Quart, request
from discord.ext import ipc

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    filename="server.log",
    datefmt="%m/%d/%Y %I:%M:%S %p",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filemode="w",
)

load_dotenv()
IPC_SECRET_KEY = os.getenv("IPC_SECRET_KEY")

app = Quart(__name__)
ipc_client = ipc.Client(secret_key=IPC_SECRET_KEY)


def authenticate_request(key):
    return key == os.getenv("API_KEY")


@app.route("/submit_application", methods=["POST"])
async def submit_application():
    app.logger.info("/submit_application post received.")

    payload = await request.get_json()

    # validate token
    if authenticate_request(payload["key"]) == False:
        app.logger.warning(f"Invalid key: {payload['key']}")
        return "Bad Request", 400

    response = await ipc_client.request("submit_application", payload=payload)
    return response


if __name__ == "__main__":
    app.run()