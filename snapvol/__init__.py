import asyncio
import snapcast.control
import argparse

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

clients = server.clients
groups = server.groups
name2client = {c.friendly_name: c for c in clients}
identifier2client = {c.identifier: c for c in clients}
name2group = {g.friendly_name: g for g in groups}

parser = argparse.ArgumentParser(
    prog="snapvol", description="Change Snapcast clients' volume."
    )
parser.add_argument(
    "--client",
    "-c",
    nargs="+",
    default=["all"],
    help='One or more clients, or "all"',
    type=str,
    choices=list(name2client.keys()).append("all"),
    )
parser.add_argument(
    "--group",
    "-g",
    nargs="+",
    default=["all"],
    help='One or more groups',
    type=str,
    choices=list(name2group.keys()).append("all"),
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
parser.add_argument("--toggle", action="store_true", help="Toggle mute status of client(s)")
parser.add_argument("--list", "-l", action="store_true", help="Print all clients and their volumes")
parser.add_argument("--absolute", "-a", action="store_true", help="Set volume rather than incrementing")
parser.add_argument(
    "--version", "-v", action="version", version="%(prog)s 0.1"
    )
args = parser.parse_args()


def main():
  if not (args.client or args.group):
    parser.error("You must specify either a client or group")

  targets = set()

  if args.client:
    if args.client == ["all"]:
      targets = set(clients)
    else:
      targets.update([name2client[name] for name in args.client])

  if args.group:
    if args.group == ["all"]:
      for g in groups:
        targets.update([identifier2client[identifier] for identifier in g.clients])
    else:
      targets.update([name2group[name] for name in args.group])

  if args.mute:
    for c in targets:
      mute(c)
  elif args.unmute:
    for c in targets:
      unmute(c)
  elif args.toggle:
    for c in targets:
      toggle_mute(c)

  elif args.list:
    for c in targets:
      get_volume(c)

  else:
    for c in targets:
      if args.absolute:
        set_volume(c, args.volume)
      else:
        change_volume(c, args.volume)

if __name__ == "__main__":
  main()
