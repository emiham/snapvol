import asyncio
import snapcast.control
import argparse
# TODO Autocompletion? Would have to work for client names
# TODO Print on no argument, flag for volume

loop = asyncio.get_event_loop()
server = loop.run_until_complete(snapcast.control.create_server(loop, '192.168.1.127'))

def change_volume(client, volume):
  new_volume = client.volume + volume
  if new_volume < 0:
    new_volume = 0
  elif new_volume > 100:
    new_volume = 100

  loop.run_until_complete(server.client_volume(client.identifier, {'percent': new_volume}))

def set_volume(client, volume):
  if volume < 0:
    volume = 0
  elif volume > 100:
    volume = 100
  loop.run_until_complete(server.client_volume(client.identifier, {'percent': volume}))

def mute(client):
  loop.run_until_complete(server.client_volume(client.identifier, {'muted': True}))

def unmute(client):
  loop.run_until_complete(server.client_volume(client.identifier, {'muted': False}))

def toggle_mute(client):
  loop.run_until_complete(server.client_volume(client.identifier, {'muted': not client.muted}))

def get_volume(client):
  print(f"{client.friendly_name}: {client.volume}")

# TODO Add groups as options (probably as another argument)
clients = server.clients
groups = server.groups
name2client = {c.friendly_name: c for c in clients}

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
    choices=name2client.keys(),
    )
parser.add_argument(
    "volume",
    nargs="?",
    default=0,
    help="Positive or negative integer to change the volume by",
    type=int,
    )
parser.add_argument("--mute", action="store_true")
parser.add_argument("--unmute", action="store_true")
parser.add_argument("--toggle", action="store_true")
parser.add_argument("--list", "-l", action="store_true")
parser.add_argument("--absolute", "-a", action="store_true")
parser.add_argument(
    "--version", "-v", action="version", version="%(prog)s 0.1"
    )
# TODO add mute positional
args = parser.parse_args()


def main():
  if args.client == "all":
    args.client = clients
  else:
    args.client = [name2client[name] for name in args.client]

  if args.mute:
    for c in args.client:
      mute(c)
  elif args.unmute:
    for c in args.client:
      unmute(c)
  elif args.toggle:
    for c in args.client:
      toggle_mute(c)

  elif args.list:
    for c in args.client:
      get_volume(c)

  else:
    for c in args.client:
      if args.absolute:
        set_volume(c, args.volume)
      else:
        change_volume(c, args.volume)

