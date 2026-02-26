"""Tests for popup queue module."""

from unittest.mock import patch
from terminal_activator.monitor import TerminalTab
from terminal_activator.queue import PopupQueue


def _tab(tty: str, fg: str = "-zsh", waiting: bool = True) -> TerminalTab:
    return TerminalTab(
        tty=tty, window_id=1, tab_index=1,
        fg_process=fg, waiting_for_input=waiting,
    )


class TestQueueBasic:
    def test_starts_idle(self):
        q = PopupQueue("/dev/ttys000")
        assert q.queue == []
        assert q.status_line == "IDLE"

    def test_excludes_own_tty(self):
        q = PopupQueue("/dev/ttys000")
        with patch("terminal_activator.queue.window_controller") as mock_wc:
            q.update([_tab("/dev/ttys000")])
        assert q.queue == []

    @patch("terminal_activator.queue.window_controller")
    def test_single_waiting_tab_enters_queue(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001")])
        assert q.queue == ["/dev/ttys001"]
        mock_wc.arrange.assert_called_once_with(["/dev/ttys001"])

    @patch("terminal_activator.queue.window_controller")
    def test_multiple_waiting_fifo_order(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002"), _tab("/dev/ttys003")])
        assert q.queue == ["/dev/ttys001", "/dev/ttys002", "/dev/ttys003"]
        mock_wc.arrange.assert_called_once_with(
            ["/dev/ttys001", "/dev/ttys002", "/dev/ttys003"]
        )

    @patch("terminal_activator.queue.window_controller")
    def test_non_waiting_tabs_excluded(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([
            _tab("/dev/ttys001", waiting=True),
            _tab("/dev/ttys002", waiting=False),
            _tab("/dev/ttys003", waiting=True),
        ])
        assert q.queue == ["/dev/ttys001", "/dev/ttys003"]


class TestQueueOrdering:
    @patch("terminal_activator.queue.window_controller")
    def test_new_waiting_added_to_end(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001")])
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")])
        # ttys001 was first, ttys002 added after
        assert q.queue == ["/dev/ttys001", "/dev/ttys002"]

    @patch("terminal_activator.queue.window_controller")
    def test_fifo_preserved_across_updates(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys002")])
        q.update([_tab("/dev/ttys002"), _tab("/dev/ttys001")])
        # ttys002 was first, even though ttys001 comes first in scan
        assert q.queue == ["/dev/ttys002", "/dev/ttys001"]

    @patch("terminal_activator.queue.window_controller")
    def test_tab_stops_waiting_removed_from_queue(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002"), _tab("/dev/ttys003")])
        # ttys002 no longer waiting (user ran command)
        q.update([
            _tab("/dev/ttys001"),
            _tab("/dev/ttys002", waiting=False),
            _tab("/dev/ttys003"),
        ])
        assert q.queue == ["/dev/ttys001", "/dev/ttys003"]

    @patch("terminal_activator.queue.window_controller")
    def test_tab_disappears_removed_from_queue(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")])
        # ttys001 window closed
        q.update([_tab("/dev/ttys002")])
        assert q.queue == ["/dev/ttys002"]

    @patch("terminal_activator.queue.window_controller")
    def test_no_duplicates(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001")])
        q.update([_tab("/dev/ttys001")])
        q.update([_tab("/dev/ttys001")])
        assert q.queue == ["/dev/ttys001"]


class TestArrangeCalls:
    @patch("terminal_activator.queue.window_controller")
    def test_arrange_called_on_queue_change(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001")])
        assert mock_wc.arrange.call_count == 1
        # New tab added → queue changed → arrange called again
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")])
        assert mock_wc.arrange.call_count == 2

    @patch("terminal_activator.queue.window_controller")
    def test_arrange_not_called_when_queue_unchanged(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001")])
        assert mock_wc.arrange.call_count == 1
        # Same state → no change → no arrange call
        q.update([_tab("/dev/ttys001")])
        assert mock_wc.arrange.call_count == 1

    @patch("terminal_activator.queue.window_controller")
    def test_arrange_not_called_when_queue_empty(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001", waiting=False)])
        mock_wc.arrange.assert_not_called()

    @patch("terminal_activator.queue.window_controller")
    def test_arrange_called_when_front_changes(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")])
        # ttys001 stops waiting → ttys002 becomes front
        q.update([_tab("/dev/ttys001", waiting=False), _tab("/dev/ttys002")])
        assert q.queue == ["/dev/ttys002"]
        mock_wc.arrange.assert_called_with(["/dev/ttys002"])


class TestStatusLine:
    @patch("terminal_activator.queue.window_controller")
    def test_idle_status(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        assert q.status_line == "IDLE"

    @patch("terminal_activator.queue.window_controller")
    def test_queue_status(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")])
        assert "QUEUE: 2" in q.status_line
        assert "FRONT: /dev/ttys001" in q.status_line

    @patch("terminal_activator.queue.window_controller")
    def test_single_queue_status(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001")])
        assert "QUEUE: 1" in q.status_line
        assert "FRONT: /dev/ttys001" in q.status_line
