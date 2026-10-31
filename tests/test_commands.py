"""Exercise real CLI parsing and commands without a running Snapserver."""

import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call, patch

from snapvol.cli import build_parser, run


def client(identifier, name, volume, muted=False):
    return Mock(
        identifier=identifier,
        friendly_name=name,
        volume=volume,
        muted=muted,
        set_volume=AsyncMock(),
        set_muted=AsyncMock(),
        set_name=AsyncMock(),
    )


class CommandTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.kitchen = client("client-1", "Kitchen", 20, muted=True)
        self.office = client("client-2", "Office", 95)
        self.group = Mock(
            identifier="group-1",
            friendly_name="Downstairs",
            clients=["client-1", "client-2"],
            set_name=AsyncMock(),
        )
        self.server = SimpleNamespace(
            clients=[self.kitchen, self.office],
            groups=[self.group],
            client=lambda identifier: next(
                c for c in [self.kitchen, self.office] if c.identifier == identifier
            ),
            start=AsyncMock(),
            stop=Mock(),
        )

    async def execute(self, *argv):
        args = build_parser().parse_args(argv)
        output = io.StringIO()
        with patch("snapvol.cli.snapcast.control.Snapserver", return_value=self.server):
            with redirect_stdout(output):
                await run(args)
        self.server.start.assert_awaited_once()
        self.server.stop.assert_called_once()
        return output.getvalue()

    async def test_absolute_volume_unmutes_only_selected_client(self):
        output = await self.execute("volume", "-c", "Kitchen", "30")
        self.kitchen.set_volume.assert_awaited_once_with(30)
        self.kitchen.set_muted.assert_awaited_once_with(False)
        self.assertEqual(
            self.kitchen.mock_calls, [call.set_muted(False), call.set_volume(30)]
        )
        self.office.set_volume.assert_not_awaited()
        self.assertIn("Kitchen 20% -> 30%", output)

    async def test_relative_volume_uses_each_clients_current_volume_and_caps_at_100(
        self,
    ):
        await self.execute("volume", "+10", "-g", "Downstairs")
        self.kitchen.set_volume.assert_awaited_once_with(30)
        self.office.set_volume.assert_awaited_once_with(100)
        self.office.set_muted.assert_not_awaited()

    async def test_negative_relative_volume_floors_at_zero(self):
        await self.execute("volume", "-30")
        self.kitchen.set_volume.assert_awaited_once_with(0)
        self.office.set_volume.assert_awaited_once_with(65)

    async def test_absolute_volume_caps_at_100(self):
        await self.execute("volume", "130", "-c", "client-2")
        self.office.set_volume.assert_awaited_once_with(100)
        self.kitchen.set_volume.assert_not_awaited()

    async def test_group_and_client_selection_deduplicates_and_honours_exclusion(self):
        await self.execute(
            "volume", "40", "-g", "group-1", "-c", "client-1", "-x", "Office"
        )
        self.kitchen.set_volume.assert_awaited_once_with(40)
        self.office.set_volume.assert_not_awaited()

    async def test_rename_client_by_name(self):
        output = await self.execute("rename", "-c", "Kitchen", "Dining room")
        self.kitchen.set_name.assert_awaited_once_with("Dining room")
        self.office.set_name.assert_not_awaited()
        self.group.set_name.assert_not_awaited()
        self.assertIn("renamed client 'Kitchen' -> 'Dining room'", output)

    async def test_rename_group_by_identifier(self):
        output = await self.execute("rename", "-g", "group-1", "Ground floor")
        self.group.set_name.assert_awaited_once_with("Ground floor")
        self.kitchen.set_name.assert_not_awaited()
        self.office.set_name.assert_not_awaited()
        self.assertIn("renamed group 'Downstairs' -> 'Ground floor'", output)

    async def test_ambiguous_rename_refuses_to_change_either_client(self):
        self.office.friendly_name = "Kitchen"
        with self.assertRaisesRegex(SystemExit, "2 clients match"):
            await self.execute("rename", "-c", "Kitchen", "New name")
        self.kitchen.set_name.assert_not_awaited()
        self.office.set_name.assert_not_awaited()
        self.server.stop.assert_called_once()

    async def test_rename_requires_exactly_one_target(self):
        with self.assertRaisesRegex(SystemExit, "exactly one"):
            await self.execute(
                "rename", "-c", "Kitchen", "-g", "Downstairs", "New name"
            )
        self.kitchen.set_name.assert_not_awaited()
        self.group.set_name.assert_not_awaited()
        self.server.stop.assert_called_once()

    async def test_unknown_volume_target_changes_nothing_and_stops_server(self):
        with self.assertRaisesRegex(SystemExit, "unknown client"):
            await self.execute("volume", "50", "-c", "Missing")
        self.kitchen.set_volume.assert_not_awaited()
        self.office.set_volume.assert_not_awaited()
        self.server.stop.assert_called_once()

    async def test_volume_failure_still_stops_server(self):
        self.office.set_volume.side_effect = RuntimeError("connection lost")
        with self.assertRaisesRegex(RuntimeError, "connection lost"):
            await self.execute("volume", "50", "-c", "Office")
        self.server.stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
