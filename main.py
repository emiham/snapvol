#!/usr/bin/env python3

import argparse
import json
import urllib.parse
import urllib.request


def request(action, **params):
    return {"id": 8, "jsonrpc": "2.0", "method": action, "params": params}


def invoke(action, **params):
    requestJson = json.dumps(request(action, **params)).encode("utf-8")
    response = json.load(
        urllib.request.urlopen(
            urllib.request.Request(
                "http://192.168.1.127:1780/jsonrpc", requestJson
            )
        )
    )
    return response["result"]


def change_volume(c, v):
    vol = invoke("Client.GetStatus", id=clients[c])["client"]["config"][
        "volume"
    ]["percent"] + int(v)
    if vol < 0:
        return invoke(
            "Client.SetVolume",
            id=clients[c],
            volume={"muted": "false", "percent": 0},
        )
    elif vol <= 100:
        return invoke(
            "Client.SetVolume",
            id=clients[c],
            volume={"muted": "false", "percent": vol},
        )


def get_volume(c):
    vol = invoke("Client.GetStatus", id=clients[c])["client"]["config"][
        "volume"
    ]["percent"]
    print(c + ":\t" + str(vol) + "%")


def mute(c):
    vol = invoke("Client.GetStatus", id=clients[c])["client"]["config"][
        "volume"
    ]["percent"]
    status = invoke("Client.GetStatus", id=clients[c])["client"]["config"][
        "volume"
    ]["muted"]
    if status == True:
        return invoke(
            "Client.SetVolume",
            id=clients[c],
            volume={"muted": False, "percent": vol},
        )
    else:
        return invoke(
            "Client.SetVolume",
            id=clients[c],
            volume={"muted": True, "percent": vol},
        )


def get_clients():
    groups = invoke("Server.GetStatus", id=1)["server"]["groups"]
    for n, g in enumerate(groups):
        print(str(n) + ": ")
        for i in g.items():
            if type(i[1]) is list:
                for c in i[1]:
                    clients[c["host"]["name"]] = c["id"]


clients = {
    # 'iwakura':  '2c:56:dc:74:7c:65',
    # 'kusanagi': '94:de:80:a3:fa:f8',
    # 'kitchen':  'b8:27:eb:2b:75:4a'
}
get_clients()

parser = argparse.ArgumentParser(
    prog="snapvol", description="Change Snapcast clients' volume."
)
# TODO negative clients (all except x)
parser.add_argument(
    "--client",
    "-c",
    nargs="+",
    default="all",
    help='One or more clients, or "all"',
    type=str,
    choices=clients,
)
parser.add_argument(
    "volume",
    nargs="?",
    default=0,
    help="Positive or negative integer to change the volume by",
    type=int,
)
parser.add_argument("--mute", action="store_true")
parser.add_argument("--list", "-l", action="store_true")
parser.add_argument(
    "--version", "-v", action="version", version="%(prog)s 0.1"
)
# TODO add mute positional
# TODO add absolute volume arg
args = parser.parse_args()


if args.mute:
    for c in args.client:
        mute(c)
elif args.list:
    if args.client == "all":
        for c in clients:
            get_volume(c)
    else:
        for c in args.client:
            get_volume(c)
else:
    if args.client == "all":
        for c in clients:
            change_volume(c, args.volume)
    else:
        for c in args.client:
            change_volume(c, args.volume)
