#!/usr/bin/python
from __future__ import print_function
from gi.repository import Gtk, Gdk, GLib, GObject
import signal
import argparse
import json
import socket
import os
import errno
import sys
import select

# FIXME: use ConfigParser or similar
clipster_dir = os.path.join(os.environ.get('HOME'), ".clipster")
sock_file = os.path.join(clipster_dir, "clipster_sock")
hist_file = os.path.join(clipster_dir, "history")
run_file = os.path.join(clipster_dir, "clipster.pid")
max_input = 50000
default_board = "PRIMARY"
client_action = "BOARD"


class Clipster(object):
    """Clipboard Manager."""

    def __init__(self, stdin):
        self.stdin = stdin

    def client(self, client_action, default_board):
        """Send a signal and (optional) data from STDIN to daemon socket."""

        message = "{0}:{1}:{2}".format(client_action,
                                       default_board,
                                       self.stdin)

        sock_c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock_c.connect(sock_file)
        sock_c.sendall(message)
        sock_c.close()


    class Daemon(object):
        def __init__(self):
            """Set up clipboard objects and history dict."""
            self.primary = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
            self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            self.boards = {"PRIMARY": [], "CLIPBOARD": []}
            self.window = self.p_id = self.c_id = sock_s = sock_c = None

        def keypress_handler(self, widget, event):
            """Handler for selection_widget keypress events."""
            # Hide window if ESC is pressed
            if (event.keyval == Gdk.KEY_Escape):
                self.window.hide()

        def selection_handler(self, tree, treepath, treecol, board):
            """Handler for selection widget 'select' event."""

            # Get selection
            model, treeiter = tree.get_selection().get_selected()
            data = model[treeiter][0]
            self.update_board(board, data)
            model.clear()
            self.window.hide()

        def selection_widget(self, board):
            self.window = Gtk.Window(title="Clipster")
            model = Gtk.ListStore(str)
            for item in self.boards[board][::-1]:
                model.append([item])

            tree = Gtk.TreeView(model)

            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn("{0} clipboard:".format(board),
                                        renderer, text=0)
            tree.append_column(column)
            self.window.connect("key-press-event", self.keypress_handler)
            # Row is clicked on, or enter pressed
            tree.connect("row-activated", self.selection_handler, board)

            self.window.add(tree)
            self.window.show_all()

        def read_history_file(self):
            """Read clipboard history from file."""
            try:
                with open(hist_file, 'r') as f:
                    self.boards.update(json.load(f))
            except IOError as exc:
                if exc.errno == errno.ENOENT:
                    # Not an error if there is no history file
                    pass

        def write_history_file(self):
            """Write clipboard history to file."""

            with open(hist_file, 'w') as f:
                json.dump(self.boards, f)

        def update_board(self, board, data):
            """Update a clipboard."""

            getattr(self, board.lower()).set_text(data, -1)

        def update_history(self, board, text):
            """Update the in-memory clipboard history."""

            # If an item already exists in the clipboard, remove it
            if text in self.boards[board]:
                self.boards[board].remove(text)
            self.boards[board].append(text)
            print(self.boards[board])

        def owner_change(self, board, event):
            """Handler for owner-change clipboard events."""

            selection = str(event.selection)
            if selection == "PRIMARY":
                event_id = self.p_id
            else:
                event_id = self.c_id
            # Some apps update primary during mouse drag (chrome)
            # Block at start to prevent repeated triggering
            board.handler_block(event_id)
            # FIXME: this devs hack is a bit verbose. Look instead at
            # gdk_seat_get_pointer -> gdk_device_get_state
            # once GdkSeat is in stable
            # FIXME: Emacs does this with ctrl-space + kb movement.
            # How to deal with this?
            # Something to do with change-owner always being same owner?
            devs = self.window.get_display().get_device_manager().list_devices(Gdk.DeviceType.MASTER)
            mouse = None
            for dev in devs:
                if dev.get_source() == Gdk.InputSource.MOUSE:
                    mouse = dev
                    break
            while (Gdk.ModifierType.BUTTON1_MASK & self.window.get_root_window().get_device_position(mouse)[3]):
                # Do nothing while mouse button is held down (selection dragging)
                pass

            # Read clipboard
            text = board.wait_for_text()
            if text:
                self.update_history(selection, text)
            # Unblock event handling
            board.handler_unblock(event_id)
            return text


        def socket_listen(self, sock_s, g_flags):
            conn, _ = sock_s.accept()
            conn.setblocking(0)
            data = []
            recv_total = 0
            while True:
                try:
                    recv = conn.recv(8192)
                    if not recv:
                        break
                    data.append(recv)
                    recv_total += len(recv)
                    if recv_total > max_input:
                        break
                except socket.error:
                    break
            if data:
                sent = ''.join(data)
                signal, content = sent.split(':', 1)
                if signal == "SELECT":
                    self.selection_widget()
                elif signal == "PRIMARY" or signal == "CLIPBOARD":
                    if content:
                        self.update_board(signal, content)
            conn.close()
            return True

        def prepare_files(self):
            """Ensure that all files and sockets used by the daemon are available."""

            # check for existing run_file, and tidy up if appropriate
            try:
                with open(run_file, 'r') as runf_r:
                    pid = int(runf_r.read())
                    try:
                        # Will do nothing, but raise an error if no such process
                        os.kill(pid, 0)
                        print("Daemon already running: pid {0}".format(pid))
                        sys.exit(1)
                    except OSError:
                        try:
                            os.unlink(run_file)
                        except IOError as exc:
                            if exc.errno == errno.ENOENT:
                               # File already gone
                              pass
                            else:
                               raise
            except IOError as exc:
                if exc.errno == errno.ENOENT:
                    pass

            # Create pid file
            with open(run_file, 'w') as runf_w:
                runf_w.write(str(os.getpid()))

            # Create the clipster dir if necessary
            try:
                os.makedirs(clipster_dir)
            except OSError as exc:
                if exc.errno == errno.EEXIST:
                    # ok if directory already exists
                    pass

            # Read in history from file
            self.read_history_file()

            # Create the socket
            try:
                os.unlink(sock_file)
            except OSError as exc:
                if exc.errno == errno.ENOENT:
                    pass

            self.sock_s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock_s.setblocking(0)
            self.sock_s.bind(sock_file)
            self.sock_s.listen(5)
            self.inputs = [self.sock_s]

        def exit(self):
            try:
                os.unlink(sock_file)
            except OSError:
                print("Warning: Failed to remove socket file: {0}".format(sock_file))
            try:
                os.unlink(run_file)
            except OSError:
                print("Warning:Failed to remove run file: {0}".format(run_file))
            self.write_history_file()
            sys.exit(0)

        def run(self):
            """Launch the clipboard manager daemon.
            Watch for clipboard events, and client (socket) connections."""

            # Set up socket, pid file etc
            self.prepare_files()

            # We need to get the display instance from the window to call get_pointer()
            # POPUP windows can do this without having to first 'show()' the window
            self.window = Gtk.Window(type=Gtk.WindowType.POPUP)

            # Handle clipboard changes
            self.p_id = self.primary.connect('owner-change', self.owner_change)
            self.c_id = self.clipboard.connect('owner-change', self.owner_change)
            # Handle socket connections
            GObject.io_add_watch(self.sock_s, GObject.IO_IN, self.socket_listen)
            # Handle unix signals
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGINT, self.exit)
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGTERM, self.exit)
            Gtk.main()



if __name__ == "__main__":

    stdin = ""
    if not sys.stdin.isatty():
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            stdin = sys.stdin.read()

    clipster = Clipster(stdin=stdin)

    parser = argparse.ArgumentParser(description='Clipster clipboard manager.')
    parser.add_argument('-p', '--primary', action="store_true", help="Write STDIN to the PRIMARY clipboard.")
    parser.add_argument('-c', '--clipboard', action="store_true", help="Write STDIN to the CLIPBOARD clipboard.")
    parser.add_argument('-d', '--daemon', action="store_true", help="Launch the daemon.")
    parser.add_argument('-s', '--select', action="store_true", help="Launch the clipboard history selection window.")

    args = parser.parse_args()

    if args.daemon:
        clipster.Daemon().run()

    if args.select:
        client_action = "SELECT"

    if args.primary:
        default_board = "PRIMARY"
    elif args.clipboard:
        default_board = "CLIPBOARD"

    clipster.client(client_action, default_board)
