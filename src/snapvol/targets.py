def resolve_targets(server, client_names, group_names, exclude_names):
    unknown = []

    def clients_named(name, what="client"):
        matches = [c for c in server.clients if name in (c.friendly_name, c.identifier)]
        if not matches:
            unknown.append(f"{what} '{name}'")
        return matches

    if not client_names and not group_names:
        selected = {c.identifier: c for c in server.clients}
    else:
        selected = {}
        for name in client_names or []:
            for c in clients_named(name):
                selected[c.identifier] = c
        for name in group_names or []:
            matches = [
                g for g in server.groups if name in (g.friendly_name, g.identifier)
            ]
            if not matches:
                unknown.append(f"group '{name}'")
            for g in matches:
                for cid in g.clients:
                    selected[cid] = server.client(cid)

    for name in exclude_names or []:
        for c in clients_named(name, "excluded client"):
            selected.pop(c.identifier, None)

    if unknown:
        raise KeyError(", ".join(unknown))
    return list(selected.values())
