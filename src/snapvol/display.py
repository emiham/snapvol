def print_clients(server, targets):
    group_of = {cid: g.friendly_name for g in server.groups for cid in g.clients}
    rows = [
        (
            c.friendly_name,
            f"{c.volume}%",
            "muted" if c.muted else "",
            "" if c.connected else "offline",
            group_of.get(c.identifier, "-"),
            c.identifier,
        )
        for c in sorted(targets, key=lambda c: c.friendly_name)
    ]

    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[1]))]

    for r in rows:
        print("  ".join(cell.ljust(w) for cell, w in zip(r, widths)).rstrip())
