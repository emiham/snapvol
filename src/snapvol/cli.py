import argparse
import asyncio
import socket
import sys

import snapcast.control

from . import (
    __version__,
    compat,  # noqa: F401
)
from .commands import cmd_list, cmd_mute, cmd_rename, cmd_volume
from .interactive import cmd_interactive
from .targets import resolve_targets


def parse_volume(s):
    try:
        return int(s), s[0] in "+-"
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid volume {s!r} (use e.g. +5, -5 or 30)"
        )


def build_parser():
    parser = argparse.ArgumentParser(
        prog="snapvol", description="Control Snapcast volume"
    )
    parser.add_argument("-H", "--host", default="localhost", help="Snapserver host")
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.set_defaults(func=cmd_list, clients=None, groups=None, excluded=None)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-c",
        "--client",
        action="append",
        dest="clients",
        metavar="NAME",
        help="client to target (repeatable)",
    )
    common.add_argument(
        "-g",
        "--group",
        action="append",
        dest="groups",
        metavar="NAME",
        help="group to target (repeatable)",
    )
    common.add_argument(
        "-x",
        "--exclude",
        action="append",
        dest="excluded",
        metavar="NAME",
        help="client to leave out (repeatable)",
    )

    sub = parser.add_subparsers(dest="verb", metavar="ACTION")

    p = sub.add_parser("list", parents=[common], aliases=["l"], help="show client info")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser(
        "volume",
        parents=[common],
        aliases=["vol", "v"],
        help="change volume: +5, -5 for relative volumes, 5 for absolute",
    )
    p.add_argument("amount", type=parse_volume, metavar="[+-]N")
    p.set_defaults(func=cmd_volume)

    p = sub.add_parser(
        "mute",
        parents=[common],
        aliases=["m"],
        help="toggle (default), mute or unmute. "
        "If the target clients have mixed states all clients will be muted.",
    )
    p.add_argument("mode", nargs="?", default="toggle", choices=["on", "off", "toggle"])
    p.set_defaults(func=cmd_mute)

    p = sub.add_parser("rename", parents=[common], help="rename one client or group")
    p.add_argument("new_name", metavar="NEW_NAME")
    p.set_defaults(func=cmd_rename)

    p = sub.add_parser(
        "interactive",
        parents=[common],
        aliases=["i"],
        help="interactive mixer",
    )
    p.set_defaults(func=cmd_interactive)

    return parser


async def run(args):
    server = snapcast.control.Snapserver(asyncio.get_running_loop(), args.host)
    await server.start()
    try:
        try:
            targets = resolve_targets(server, args.clients, args.groups, args.excluded)
        except KeyError as e:
            sys.exit(f"snapvol: unknown {e.args[0]}")
        if not targets:
            sys.exit("snapvol: no clients selected")
        await args.func(server, args, targets)
    finally:
        server.stop()


def main():
    args = build_parser().parse_args()
    try:
        asyncio.run(run(args))
    except (ConnectionRefusedError, TimeoutError, socket.gaierror) as e:
        sys.exit(f"snapvol: cannot reach {args.host}: {e}")
