"""Tests for popup queue module."""

from unittest.mock import patch
from mtt.monitor import TerminalTab
from mtt.queue import PopupQueue


def _tab(tty: str, fg: str = "-zsh", waiting: bool = True,
         idle_reason: str = "marker") -> TerminalTab:
    return TerminalTab(
        tty=tty, window_id=1, tab_index=1,
        fg_process=fg, waiting_for_input=waiting,
        idle_reason=idle_reason if waiting else "",
    )


class TestQueueBasic:
    def test_starts_idle(self):
        q = PopupQueue("/dev/ttys000")
        assert q.queue == []
        assert q.status_line == "IDLE"

    def test_excludes_own_tty(self):
        q = PopupQueue("/dev/ttys000")
        with patch("mtt.queue.window_controller"):
            q.update([_tab("/dev/ttys000")], "")
        assert q.queue == []

    @patch("mtt.queue.window_controller")
    def test_single_waiting_tab_enters_queue(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001")], "")
        assert q.queue == ["/dev/ttys001"]
        mock_wc.popup.assert_called_once_with("/dev/ttys001")

    @patch("mtt.queue.window_controller")
    def test_multiple_waiting_fifo_order(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002"), _tab("/dev/ttys003")], "")
        assert q.queue == ["/dev/ttys001", "/dev/ttys002", "/dev/ttys003"]

    @patch("mtt.queue.window_controller")
    def test_non_waiting_tabs_excluded(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([
            _tab("/dev/ttys001", waiting=True),
            _tab("/dev/ttys002", waiting=False),
            _tab("/dev/ttys003", waiting=True),
        ], "")
        assert q.queue == ["/dev/ttys001", "/dev/ttys003"]


class TestQueueOrdering:
    @patch("mtt.queue.window_controller")
    def test_new_waiting_added_to_end(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001")], "")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "/dev/ttys001")
        assert q.queue == ["/dev/ttys001", "/dev/ttys002"]

    @patch("mtt.queue.window_controller")
    def test_fifo_preserved_across_updates(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys002")], "")
        q.update([_tab("/dev/ttys002"), _tab("/dev/ttys001")], "/dev/ttys002")
        assert q.queue == ["/dev/ttys002", "/dev/ttys001"]

    @patch("mtt.queue.window_controller")
    def test_tab_stops_waiting_removed_from_queue(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "")
        q.update([
            _tab("/dev/ttys001", waiting=False),
            _tab("/dev/ttys002"),
        ], "/dev/ttys001")
        assert q.queue == ["/dev/ttys002"]

    @patch("mtt.queue.window_controller")
    def test_no_duplicates(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001")], "")
        q.update([_tab("/dev/ttys001")], "/dev/ttys001")
        assert q.queue == ["/dev/ttys001"]


class TestServingBehavior:
    @patch("mtt.queue.window_controller")
    def test_serving_set_on_first_idle(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "")
        assert q.serving == "/dev/ttys001"

    @patch("mtt.queue.window_controller")
    def test_no_switch_while_serving_idle(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "")
        count = mock_wc.popup.call_count
        # Serving terminal still idle → no rearrange
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "/dev/ttys001")
        assert mock_wc.popup.call_count == count

    @patch("mtt.queue.window_controller")
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

    @patch("mtt.queue.window_controller")
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

    @patch("mtt.queue.window_controller")
    def test_serving_syncs_to_frontmost_idle(self, mock_wc):
        """If user switches to a different idle terminal, serving follows."""
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "")
        assert q.serving == "/dev/ttys001"
        # User manually switches to ttys002
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "/dev/ttys002")
        assert q.serving == "/dev/ttys002"

    @patch("mtt.queue.window_controller")
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

    @patch("mtt.queue.window_controller")
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

    @patch("mtt.queue.window_controller")
    def test_no_sync_when_terminal_app_not_active(self, mock_wc):
        """If Terminal.app is not active (frontmost_tty=""), don't change serving."""
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "")
        assert q.serving == "/dev/ttys001"
        # Terminal.app not frontmost
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "")
        assert q.serving == "/dev/ttys001"


class TestShellExclusion:
    """Shell-only idle terminals must NOT enter the popup queue."""

    @patch("mtt.queue.window_controller")
    def test_shell_only_terminal_excluded_from_queue(self, mock_wc):
        """A new terminal at shell prompt should not enter queue."""
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001", idle_reason="shell")], "")
        assert q.queue == []
        mock_wc.popup.assert_not_called()

    @patch("mtt.queue.window_controller")
    def test_shell_terminal_does_not_trigger_popup(self, mock_wc):
        """Typing in a shell terminal should not popup idle Claude sessions."""
        q = PopupQueue("/dev/ttys000")
        # Claude session idle (marker), plus a shell terminal
        q.update([
            _tab("/dev/ttys001", idle_reason="marker"),
            _tab("/dev/ttys002", idle_reason="shell"),
        ], "/dev/ttys002")
        mock_wc.popup.reset_mock()
        # User types in shell terminal → it becomes busy
        q.update([
            _tab("/dev/ttys001", idle_reason="marker"),
            _tab("/dev/ttys002", waiting=False),
        ], "/dev/ttys002")
        # Should NOT popup ttys001 — user is working in a regular terminal
        mock_wc.popup.assert_not_called()
        # serving should stay as ttys001 (was set when no serving existed)
        assert q.serving == "/dev/ttys001"

    @patch("mtt.queue.window_controller")
    def test_marker_terminal_still_queued(self, mock_wc):
        """Terminals with idle marker should still be queued normally."""
        q = PopupQueue("/dev/ttys000")
        q.update([
            _tab("/dev/ttys001", idle_reason="marker"),
            _tab("/dev/ttys002", idle_reason="shell"),
        ], "")
        assert q.queue == ["/dev/ttys001"]
        assert "/dev/ttys002" not in q.queue

    @patch("mtt.queue.window_controller")
    def test_stasis_terminal_still_queued(self, mock_wc):
        """Terminals with stasis detection should still be queued."""
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001", idle_reason="stasis")], "")
        assert q.queue == ["/dev/ttys001"]


class TestStasisHoldoff:
    """Stasis-served terminals must not switch away when user is typing."""

    @patch("mtt.queue.window_controller")
    def test_stasis_typing_no_popup(self, mock_wc):
        """User types in stasis-idle terminal → content changes → no popup."""
        q = PopupQueue("/dev/ttys000")
        # A idle via stasis, B idle via marker. A gets served.
        q.update([
            _tab("/dev/ttys001", idle_reason="stasis"),
            _tab("/dev/ttys002", idle_reason="marker"),
        ], "/dev/ttys001")
        assert q.serving == "/dev/ttys001"
        mock_wc.popup.reset_mock()
        # User types in A → stasis resets → A leaves waiting_ttys
        q.update([
            _tab("/dev/ttys001", waiting=False),
            _tab("/dev/ttys002", idle_reason="marker"),
        ], "/dev/ttys001")
        # Should NOT switch — user is looking at stasis terminal
        assert q.serving == "/dev/ttys001"
        mock_wc.popup.assert_not_called()

    @patch("mtt.queue.window_controller")
    def test_stasis_holdoff_releases_on_focus_away(self, mock_wc):
        """User finishes typing and looks away → switch to next."""
        q = PopupQueue("/dev/ttys000")
        q.update([
            _tab("/dev/ttys001", idle_reason="stasis"),
            _tab("/dev/ttys002", idle_reason="marker"),
        ], "/dev/ttys001")
        mock_wc.popup.reset_mock()
        # User types → A leaves waiting_ttys, but still frontmost
        q.update([
            _tab("/dev/ttys001", waiting=False),
            _tab("/dev/ttys002", idle_reason="marker"),
        ], "/dev/ttys001")
        assert q.serving == "/dev/ttys001"
        # User looks away (switches to another app or terminal)
        q.update([
            _tab("/dev/ttys001", waiting=False),
            _tab("/dev/ttys002", idle_reason="marker"),
        ], "")
        # NOW should switch to B
        assert q.serving == "/dev/ttys002"
        mock_wc.popup.assert_called_with("/dev/ttys002")

    @patch("mtt.queue.window_controller")
    def test_stasis_becomes_idle_again(self, mock_wc):
        """Stasis terminal becomes idle again after typing → serving re-syncs."""
        q = PopupQueue("/dev/ttys000")
        q.update([
            _tab("/dev/ttys001", idle_reason="stasis"),
            _tab("/dev/ttys002", idle_reason="marker"),
        ], "/dev/ttys001")
        mock_wc.popup.reset_mock()
        # User types → A leaves waiting, held off
        q.update([
            _tab("/dev/ttys001", waiting=False),
            _tab("/dev/ttys002", idle_reason="marker"),
        ], "/dev/ttys001")
        # A becomes idle again (user paused typing, stasis re-triggers)
        q.update([
            _tab("/dev/ttys001", idle_reason="stasis"),
            _tab("/dev/ttys002", idle_reason="marker"),
        ], "/dev/ttys001")
        # Serving should re-sync to A (frontmost + idle)
        assert q.serving == "/dev/ttys001"
        mock_wc.popup.assert_not_called()

    @patch("mtt.queue.window_controller")
    def test_marker_still_switches_immediately(self, mock_wc):
        """Marker-based serving terminal switches immediately on submit."""
        q = PopupQueue("/dev/ttys000")
        q.update([
            _tab("/dev/ttys001", idle_reason="marker"),
            _tab("/dev/ttys002", idle_reason="marker"),
        ], "/dev/ttys001")
        mock_wc.popup.reset_mock()
        # User submits → marker removed → A not waiting
        q.update([
            _tab("/dev/ttys001", waiting=False),
            _tab("/dev/ttys002", idle_reason="marker"),
        ], "/dev/ttys001")
        # Should switch immediately (marker = definitive submit signal)
        assert q.serving == "/dev/ttys002"
        mock_wc.popup.assert_called_with("/dev/ttys002")

    @patch("mtt.queue.window_controller")
    def test_stasis_upgrades_to_marker(self, mock_wc):
        """Stasis-served terminal gets marker → submit switches immediately."""
        q = PopupQueue("/dev/ttys000")
        # A idle via stasis
        q.update([
            _tab("/dev/ttys001", idle_reason="stasis"),
            _tab("/dev/ttys002", idle_reason="marker"),
        ], "/dev/ttys001")
        # A gets marker (Claude finished turn, Stop hook fired)
        q.update([
            _tab("/dev/ttys001", idle_reason="marker"),
            _tab("/dev/ttys002", idle_reason="marker"),
        ], "/dev/ttys001")
        assert q.serving_reason == "marker"
        mock_wc.popup.reset_mock()
        # User submits → marker removed
        q.update([
            _tab("/dev/ttys001", waiting=False),
            _tab("/dev/ttys002", idle_reason="marker"),
        ], "/dev/ttys001")
        # Should switch immediately (now marker-based)
        assert q.serving == "/dev/ttys002"
        mock_wc.popup.assert_called_with("/dev/ttys002")


class TestStatusLine:
    @patch("mtt.queue.window_controller")
    def test_idle_status(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        assert q.status_line == "IDLE"

    @patch("mtt.queue.window_controller")
    def test_queue_status(self, mock_wc):
        q = PopupQueue("/dev/ttys000")
        q.update([_tab("/dev/ttys001"), _tab("/dev/ttys002")], "")
        assert "QUEUE: 2" in q.status_line
        assert "SERVING: /dev/ttys001" in q.status_line
