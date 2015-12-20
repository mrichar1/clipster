from gi.repository import Gtk, Gdk, GLib
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)
import time
import argparse
import json


boards = {"primary": [],
               "secondary": []}

class Clips(Gtk.Clipboard):

    def __init__(self):
        self.primary = self.get(Gdk.SELECTION_PRIMARY)
        self.clipboard = self.get(Gdk.SELECTION_CLIPBOARD)
        # Owner change happens for both board, regardless of which type is actually receiving data. So compare previous last entry for that board to the current one, and print if different.Also try to find a nicer way to do the 'which id should I block' stuff...'


class Clipster(object):
    def __init__(self):
        self.clips = Clips()
	self.boards = {"primary": [], "secondary": []}
	self.window = self.pid = self.cid = None

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
	    if temp in boards[board_type]:
	        boards[board_type].remove(temp)
	    boards[board_type].append(temp)
	print(boards[board_type])
        # Unblock event handling
	board.handler_unblock(event_id)

    def daemon():
        # Create a Window class instance, as creating a Display()
        # instance and calling get_pointer() from it segfaults
        self.window = Gtk.Window(type=Gtk.WindowType.POPUP)
        self.pid = self.clips.primary.connect('owner-change', self.read_from_clip, "primary")
        self.cid = self.clips.clipboard.connect('owner-change', self.read_from_clip, "clipboard")
        Gtk.main()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-l', '--list', action="store_true", help="")
    parser.add_argument('-d', '--daemon', action="store_true", help="")

    args = parser.parse_args()

    clipster = Clipster()
    if args.daemon:
	clipster.daemon()

    if args.list:
        print(' '.join(boards['primary']))




