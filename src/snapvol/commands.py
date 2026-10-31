import asyncio
import sys

from .display import print_clients


async def cmd_list(server, _, targets):
    print_clients(server, targets)


async def cmd_mute(_, args, targets):
    if args.mode == "toggle":
        muted = not all(c.muted for c in targets)
    else:
        muted = args.mode == "on"
    await asyncio.gather(*(c.set_muted(muted) for c in targets))
    print(
        ("muted " if muted else "unmuted ")
        + ", ".join(c.friendly_name for c in targets)
    )


async def cmd_volume(_, args, targets):
    value, relative = args.amount

    async def one(c):
        old = c.volume
        new = max(0, min(100, old + value if relative else value))
        if c.muted:
            await c.set_muted(False)
        await c.set_volume(new)
        return f"{c.friendly_name} {old}% -> {new}%"

    for line in await asyncio.gather(*(one(c) for c in targets)):
        print(line)


async def cmd_rename(server, args, _):
    if args.excluded:
        sys.exit("snapvol rename: -x can't be used here")
    given = (args.clients or []) + (args.groups or [])
    if len(given) != 1:
        sys.exit("snapvol rename: give exactly one client (-c) or one group (-g)")

    if args.clients:
        kind, old, pool = "client", args.clients[0], server.clients
    else:
        kind, old, pool = "group", args.groups[0], server.groups

    matches = [o for o in pool if old in (o.friendly_name, o.identifier)]
    if len(matches) != 1:
        ids = ", ".join(o.identifier for o in matches)
        sys.exit(
            f"snapvol rename: {len(matches)} {kind}s match '{old}'; use an ID: {ids}"
        )

    obj = matches[0]
    old_name = obj.friendly_name  # save before the await
    await obj.set_name(args.new_name)
    print(f"renamed {kind} '{old_name}' -> '{args.new_name}'")
