from gi.repository import Gtk, Gdk, GLib, GObject
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)
import time
import argparse
import json
import atexit
import socket
import os
import sys
import select

# FIXME: better place for this
sock_address = "/tmp/.clipster_sock"


class Clips(Gtk.Clipboard):

    def __init__(self):
        self.primary = self.get(Gdk.SELECTION_PRIMARY)
        self.clipboard = self.get(Gdk.SELECTION_CLIPBOARD)
        # Owner change happens for both board, regardless of which type is actually receiving data. So compare previous last entry for that board to the current one, and print if different.Also try to find a nicer way to do the 'which id should I block' stuff...'


class Clipster(object):
    def __init__(self):
        self.clips = Clips()
        self.boards = {"primary": [], "clipboard": []}
        self.window = self.pid = self.cid = None
        self.histfile = "/home/mrichar1/.clipster_history"
        atexit.register(self.write_history_file)

    def write_history_file(self):
        with open(self.histfile, 'w') as f:
            json.dump(self.boards, f)

    def client(self, board):
        stdin = ""
        if sys.stdin in select.select([sys.stdin],[],[],0)[0]:
            stdin = sys.stdin.read()

        message = "{0}:{1}".format(board, stdin)

        self.sock_c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock_c.connect(sock_address)

        self.sock_c.sendall(message)
        data = self.sock_c.recv(1024)
        if data:
            print(data)
        self.sock_c.close()

    def read_from_clip(self, board, _, board_type):
        if board_type == "primary":
	    event_id = self.pid
        else:
            event_id = self.cid
        # Some apps update primary during mouse drag (chrome)
        # Block at start to prevent repeated triggering
        board.handler_block(event_id)
        while int(self.window.get_display().get_pointer()[3]):
            # Do nothing while mouse buttons are held down
            pass

        # Read clipboard
        temp = board.wait_for_text()
        if temp:
	    # Rempve existing item (before adding to end)
	    if temp in self.boards[board_type]:
	        self.boards[board_type].remove(temp)
	    self.boards[board_type].append(temp)
	print(self.boards[board_type])
        # Unblock event handling
	board.handler_unblock(event_id)

    def start_server(self):
        try:
            os.unlink(sock_address)
        except OSError: # FIXME: use better io error handling than this
            if os.path.exists(sock_address):
                raise

        self.sock_s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock_s.setblocking(0)
        self.sock_s.bind(sock_address)
        self.sock_s.listen(5)
        self.inputs = [self.sock_s]


    def ipc(self, sock_s, g_flags):
        conn, _ = sock_s.accept()
        conn.setblocking(0)
        data = []
        while True:
            try:
                recv = conn.recv(8192)
                if not recv:
                    break
                data.append(recv)
            except socket.error:
                break
        if data:
            sent = ''.join(data)
            board, content = sent.split(':', 1)
            if board == "P":
                if content:
                    self.clips.primary.set_text(content, len=-1)
                else:
                    conn.sendall('\n\n'.join(self.boards["primary"][::-1]))
            elif board == "C":
                if content:
                    self.clips.primary.set_text(content, len=-1)
                else:
                    conn.sendall('\n\n'.join(self.boards["clipboard"][::-1]))
        conn.close()
        return True


    def daemon(self):
        # Create a Window class instance, as creating a Display()
        # instance and calling get_pointer() from it segfaults
        self.window = Gtk.Window(type=Gtk.WindowType.POPUP)
        self.pid = self.clips.primary.connect('owner-change', self.read_from_clip, "primary")
        self.cid = self.clips.clipboard.connect('owner-change', self.read_from_clip, "clipboard")
        self.start_server()
        GObject.io_add_watch(self.sock_s, GObject.IO_IN, self.ipc)
        Gtk.main()


if __name__ == "__main__":


    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-p', '--primary', action="store_true", help="")
    parser.add_argument('-c', '--clipboard', action="store_true", help="")
    parser.add_argument('-d', '--daemon', action="store_true", help="")

    args = parser.parse_args()

    clipster = Clipster()
    if args.daemon:
	clipster.daemon()
        sys.exit()

    if args.primary:
        clipster.client("P")
    if args.clipboard:
        clipster.client("C")
