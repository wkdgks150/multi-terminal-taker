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
        with patch("terminal_activator.queue.window_controller"):
            q.update([_tab("/dev/ttys000")], "")
        assert q.queue == []

    @patch("terminal_activator.queue.window_controller")
    def test_single_waiting_tab_enters_queue(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001")], "")
        assert q.queue == ["/dev/ttys001"]
        mock_wc.popup.assert_called_once_with("/dev/ttys001")

    @patch("terminal_activator.queue.window_controller")
    def test_multiple_waiting_fifo_order(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002"), _tab("/dev/ttys003")], "")
        assert q.queue == ["/dev/ttys001", "/dev/ttys002", "/dev/ttys003"]

    @patch("terminal_activator.queue.window_controller")
    def test_non_waiting_tabs_excluded(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([
            _tab("/dev/ttys001", waiting=True),
            _tab("/dev/ttys002", waiting=False),
            _tab("/dev/ttys003", waiting=True),
        ], "")
        assert q.queue == ["/dev/ttys001", "/dev/ttys003"]


class TestQueueOrdering:
    @patch("terminal_activator.queue.window_controller")
    def test_new_waiting_added_to_end(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001")], "")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "/dev/ttys001")
        assert q.queue == ["/dev/ttys001", "/dev/ttys002"]

    @patch("terminal_activator.queue.window_controller")
    def test_fifo_preserved_across_updates(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys002")], "")
        q.update([_tab("/dev/ttys002"), _tab("/dev/ttys001")], "/dev/ttys002")
        assert q.queue == ["/dev/ttys002", "/dev/ttys001"]

    @patch("terminal_activator.queue.window_controller")
    def test_tab_stops_waiting_removed_from_queue(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "")
        q.update([
            _tab("/dev/ttys001", waiting=False),
            _tab("/dev/ttys002"),
        ], "/dev/ttys001")
        assert q.queue == ["/dev/ttys002"]

    @patch("terminal_activator.queue.window_controller")
    def test_no_duplicates(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001")], "")
        q.update([_tab("/dev/ttys001")], "/dev/ttys001")
        assert q.queue == ["/dev/ttys001"]


class TestServingBehavior:
    @patch("terminal_activator.queue.window_controller")
    def test_serving_set_on_first_idle(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "")
        assert q.serving == "/dev/ttys001"

    @patch("terminal_activator.queue.window_controller")
    def test_no_switch_while_serving_idle(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "")
        count = mock_wc.popup.call_count
        # Serving terminal still idle → no rearrange
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "/dev/ttys001")
        assert mock_wc.popup.call_count == count

    @patch("terminal_activator.queue.window_controller")
    def test_switch_when_serving_becomes_busy(self, mock_wc):
        """When SERVING terminal becomes BUSY (user submitted prompt), switch."""
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "")
        assert q.serving == "/dev/ttys001"
        # User submits prompt in ttys001 → hook removes marker → not waiting
        q.update([
            _tab("/dev/ttys001", waiting=False),
            _tab("/dev/ttys002"),
        ], "/dev/ttys001")
        # Should switch to ttys002
        assert q.serving == "/dev/ttys002"
        mock_wc.popup.assert_called_with("/dev/ttys002")

    @patch("terminal_activator.queue.window_controller")
    def test_no_switch_when_no_idle_terminals(self, mock_wc):
        """When SERVING becomes busy but no idle terminals exist, just clear."""
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001")], "")
        assert q.serving == "/dev/ttys001"
        # Both busy
        q.update([_tab("/dev/ttys001", waiting=False)], "/dev/ttys001")
        assert q.serving is None
        assert q.status_line == "IDLE"


class TestFrontmostSync:
    """serving must follow frontmost_tty so popups match what user is looking at."""

    @patch("terminal_activator.queue.window_controller")
    def test_serving_syncs_to_frontmost_idle(self, mock_wc):
        """If user switches to a different idle terminal, serving follows."""
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "")
        assert q.serving == "/dev/ttys001"
        # User manually switches to ttys002
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "/dev/ttys002")
        assert q.serving == "/dev/ttys002"

    @patch("terminal_activator.queue.window_controller")
    def test_popup_after_user_sends_from_non_serving(self, mock_wc):
        """User looks at ttys002 (not serving) and sends message → next idle pops up."""
        q = PopupQueue("/dev/ttys000")
        # A goes idle first → serving = A
        q.update([_tab("/dev/ttys001")], "")
        assert q.serving == "/dev/ttys001"
        # B also goes idle, user is looking at B
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "/dev/ttys002")
        # serving should sync to B (what user is looking at)
        assert q.serving == "/dev/ttys002"
        # User sends message in B → B becomes busy
        mock_wc.popup.reset_mock()
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002", waiting=False)], "/dev/ttys002")
        # Should switch to A
        assert q.serving == "/dev/ttys001"
        mock_wc.popup.assert_called_with("/dev/ttys001")

    @patch("terminal_activator.queue.window_controller")
    def test_no_sync_when_frontmost_busy(self, mock_wc):
        """If frontmost is busy, don't change serving."""
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "")
        assert q.serving == "/dev/ttys001"
        # User is on ttys003 (busy, not in queue)
        q.update([
            _tab("/dev/ttys001"), _tab("/dev/ttys002"),
            _tab("/dev/ttys003", waiting=False),
        ], "/dev/ttys003")
        # serving stays as ttys001
        assert q.serving == "/dev/ttys001"

    @patch("terminal_activator.queue.window_controller")
    def test_no_sync_when_terminal_app_not_active(self, mock_wc):
        """If Terminal.app is not active (frontmost_tty=""), don't change serving."""
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "")
        assert q.serving == "/dev/ttys001"
        # Terminal.app not frontmost
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "")
        assert q.serving == "/dev/ttys001"


class TestStatusLine:
    @patch("terminal_activator.queue.window_controller")
    def test_idle_status(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        assert q.status_line == "IDLE"

    @patch("terminal_activator.queue.window_controller")
    def test_queue_status(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "")
        assert "QUEUE: 2" in q.status_line
        assert "SERVING: /dev/ttys001" in q.status_line
