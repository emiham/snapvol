import asyncio
import curses
import locale
import os
import sys

HELP = "j/k select  h/l volume  H/L fine  0-9 set  m mute  q quit"
FILLED = "━"
EMPTY = "╌"
CARD = 3


class Mixer:
    def __init__(self, server, screen, clients, stop):
        self.server = server
        self.screen = screen
        self.clients = clients
        self.stop = stop
        self.selected = None
        self.show_offline = False
        self.scroll = 0
        self.width = 0
        self.rows = []
        self.order = []
        self.tasks = set()
        self.colors = self.init_colors()

    def init_colors(self):
        if not curses.has_colors():
            return {}
        curses.start_color()
        curses.use_default_colors()
        names = ("low", "mid", "high", "accent")
        colors = (
            curses.COLOR_GREEN,
            curses.COLOR_YELLOW,
            curses.COLOR_RED,
            curses.COLOR_CYAN,
        )
        for pair, color in enumerate(colors, 1):
            curses.init_pair(pair, color, -1)
        return {name: curses.color_pair(i) for i, name in enumerate(names, 1)}

    def color(self, name):
        return self.colors.get(name, 0)

    def put(self, y, x, text, attr=0):
        try:
            self.screen.addstr(y, x, text[: max(0, self.width - x - 1)], attr)
        except curses.error:
            pass

    def refresh(self):
        by_id = {c.identifier: c for c in self.clients}
        rows = []
        for g in self.server.groups:
            members = sorted(
                (
                    by_id[cid]
                    for cid in g.clients
                    if cid in by_id and (self.show_offline or by_id[cid].connected)
                ),
                key=lambda c: c.friendly_name,
            )
            if members:
                rows.append(("group", g))
                rows.extend(("client", c) for c in members)
        self.rows = rows
        self.order = [obj for kind, obj in rows if kind == "client"]
        ids = [c.identifier for c in self.order]
        if self.selected not in ids:
            self.selected = ids[0] if ids else None

    def draw(self):
        self.refresh()
        screen = self.screen
        screen.erase()
        height, self.width = screen.getmaxyx()
        body = max(1, height - 1)

        ys = []
        y = 0
        for kind, _ in self.rows:
            ys.append(y)
            y += CARD if kind == "client" else 1

        for i, (kind, obj) in enumerate(self.rows):
            if kind == "client" and obj.identifier == self.selected:
                start = ys[i - 1] if i > 0 and self.rows[i - 1][0] == "group" else ys[i]
                end = ys[i] + CARD
                if start < self.scroll:
                    self.scroll = start
                elif end > self.scroll + body:
                    self.scroll = end - body
        self.scroll = max(0, min(self.scroll, y - body))

        for (kind, obj), row_y in zip(self.rows, ys):
            height_of_row = CARD if kind == "client" else 1
            top = row_y - self.scroll
            if top < 0 or top + height_of_row > body:
                continue
            if kind == "group":
                self.draw_group(top, obj)
            else:
                self.draw_client(top, obj, obj.identifier == self.selected)

        if height > 1:
            offline = sum(not c.connected for c in self.clients)
            footer = HELP
            if offline:
                verb = "hide" if self.show_offline else "show"
                noun = "client" if offline == 1 else "clients"
                footer += f"  o {verb} {offline} offline {noun}"
            self.put(height - 1, 0, footer, curses.A_DIM)
        screen.refresh()

    def draw_group(self, y, g):
        name = g.friendly_name
        self.put(y, 0, "──", curses.A_DIM)
        self.put(y, 3, name, curses.A_BOLD)
        self.put(y, 4 + len(name), "─" * self.width, curses.A_DIM)

    def draw_client(self, y, c, selected):
        width = self.width
        offline = not c.connected
        muted = c.muted
        faded = curses.A_DIM if muted or offline else 0
        emphasis = curses.A_BOLD if selected else 0

        if selected:
            marker = self.color("accent") | curses.A_BOLD
            self.put(y, 0, "▌", marker)
            self.put(y + 1, 0, "▌", marker)

        status = "offline" if offline else "muted" if muted else ""
        name = c.friendly_name[: max(1, width - 4)]
        self.put(y, 2, name, emphasis | faded)
        if status:
            attr = curses.A_DIM if offline else self.color("mid")
            self.put(y, width - len(status) - 2, status, attr)

        bar_width = max(0, width - 9)
        filled = round(bar_width * c.volume / 100)
        for i in range(bar_width):
            if i < filled:
                position = (i + 1) / bar_width
                shade = (
                    "low" if position <= 0.6 else "mid" if position <= 0.85 else "high"
                )
                attr = curses.A_DIM if muted or offline else self.color(shade)
                self.put(y + 1, 2 + i, FILLED, attr)
            else:
                self.put(y + 1, 2 + i, EMPTY, curses.A_DIM)
        self.put(y + 1, 3 + bar_width, f"{c.volume:>3}%", emphasis | faded)

    def handle_keys(self):
        while True:
            key = self.screen.getch()
            if key == -1:
                break
            self.press(key)
        self.draw()

    def press(self, key):
        self.refresh()
        if key in (ord("q"), 27):
            self.stop.set()
            return
        if key == ord("o"):
            self.show_offline = not self.show_offline
            return
        if not self.order:
            return
        ids = [c.identifier for c in self.order]
        i = ids.index(self.selected)
        c = self.order[i]
        if key in (ord("j"), curses.KEY_DOWN):
            self.selected = ids[min(i + 1, len(ids) - 1)]
        elif key in (ord("k"), curses.KEY_UP):
            self.selected = ids[max(i - 1, 0)]
        elif key in (ord("l"), curses.KEY_RIGHT):
            self.change(c, c.volume + 5)
        elif key in (ord("h"), curses.KEY_LEFT):
            self.change(c, c.volume - 5)
        elif key == ord("L"):
            self.change(c, c.volume + 1)
        elif key == ord("H"):
            self.change(c, c.volume - 1)
        elif key == ord("m"):
            self.spawn(c.set_muted(not c.muted))
        elif ord("0") <= key <= ord("9"):
            self.change(c, (key - ord("0") or 10) * 10)

    def change(self, c, level):
        self.spawn(self.apply(c, max(0, min(100, level))))

    async def apply(self, c, level):
        if c.muted:
            await c.set_muted(False)
        await c.set_volume(level)

    def spawn(self, coro):
        task = asyncio.ensure_future(coro)
        self.tasks.add(task)
        task.add_done_callback(self.finished)

    def finished(self, task):
        self.tasks.discard(task)
        if not task.cancelled():
            task.exception()
        self.draw()


async def cmd_interactive(server, _, targets):
    if not sys.stdin.isatty():
        sys.exit("snapvol: interactive mode needs a terminal")
    locale.setlocale(locale.LC_ALL, "")
    os.environ.setdefault("ESCDELAY", "25")
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    screen = curses.initscr()
    mixer = Mixer(server, screen, list(targets), stop)
    try:
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        screen.keypad(True)
        screen.nodelay(True)
        for c in mixer.clients:
            c.set_callback(lambda _: mixer.draw())
        loop.add_reader(sys.stdin.fileno(), mixer.handle_keys)
        mixer.draw()
        await stop.wait()
    finally:
        loop.remove_reader(sys.stdin.fileno())
        for c in mixer.clients:
            c.set_callback(None)
        curses.nocbreak()
        screen.keypad(False)
        curses.echo()
        curses.endwin()
    if mixer.tasks:
        await asyncio.gather(*mixer.tasks, return_exceptions=True)
