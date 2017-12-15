#!/usr/bin/python
# vim: set fileencoding=utf-8 :

import unittest
import os
import errno
import logging
import json
from gi import require_version
require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

try:
    # py 3.x
    from unittest import mock
except ImportError:
    # py 2.x
    import mock

try:
    # py >=3.5
    import importlib.util
    spec = importlib.util.spec_from_file_location("clipster", "clipster")
    clipster = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(clipster)
except AttributeError:
    # py 3.3 or 3.4
    try:
        from importlib.machinery import SourceFileLoader
        clipster = SourceFileLoader("clipster", "clipster").load_module()
    except ImportError:
        import imp
        clipster = imp.load_source('clipster', 'clipster')
except ImportError:
    # py 2.x
    import imp
    clipster = imp.load_source('clipster', 'clipster')

try:
    # py 3.x
    import builtins
except ImportError:
    # py 2.x
    import __builtin__ as builtins


class ClipsterTestCase(unittest.TestCase):
    """Test the 'global' classes/methods of Clipster."""

    def test_suppress_if_errno_suppress(self):
        """Should NOT raise an OSError exception."""

        with clipster.suppress_if_errno(OSError, errno.EEXIST):
            raise OSError(errno.EEXIST, "")

    def test_suppress_if_errno_raise(self):
        """Should raise an OSError exception."""

        with self.assertRaises(OSError):
            with clipster.suppress_if_errno(OSError, errno.EEXIST):
                raise OSError(errno.ENOENT, "")

    def test_ClipsterError(self):
        """ClipsterError can be raised."""

        with self.assertRaises(clipster.ClipsterError) as exc:
            raise clipster.ClipsterError()


class ClientTestCase(unittest.TestCase):
    """We mock a socket - however due to the underlying C library, we can't just mock
    socket.socket and get a handle all the way down the stack, so we have to 'know'
    that the client maps this to 'sock'."""

    @classmethod
    def setUpClass(cls):
        # Read in the config and args defaults
        cls.args = clipster.parse_args()
        # 2nd argument is the data dir - usually derived from XDG/ENV
        # Set to an explicit value for testing
        cls.data_dir = "/data_dir"
        cls.conf_dir = "/conf_dir"
        cls.config = clipster.parse_config(cls.args, cls.data_dir, cls.conf_dir)
        cls.logger = logging.getLogger()
#        cls.logger.level = logging.DEBUG

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        # Set up a fake history
        self.history = {"CLIPBOARD": ["ape", "bear\nbear", "cat\ncat\n"], "PRIMARY": ["apple", "banana\nbanana", "clementine\nclementine\n"]}

    def tearDown(self):
        self.history = None

    def test_unittest(self):
        """Test that unit testing is actually working."""
        self.assertTrue(True)

    @mock.patch('clipster.socket.socket')
    def test_client_update(self, mock_socket):
        """Does the client connect and send data as expected?"""

        board = self.config.get('clipster', 'default_selection')
        socket_file = self.config.get('clipster', 'socket_file')
        client_action = "SELECT"
        self.args.select = True
        self.client = clipster.Client(self.config, self.args)
        self.client.update()
        # Get a handle to the sock object returned by the mocked socket.socket
        sock = mock_socket.return_value
        self.assertTrue(mock.call.connect(os.path.join(self.data_dir, socket_file)) in sock.mock_calls)
        self.assertTrue(mock.call.sendall('{}:{}:0'.format(client_action, board).encode('utf-8')) in sock.mock_calls)

    @mock.patch('clipster.socket.socket')
    def test_client_output(self, mock_socket):
        """Does the client connect, send and receive data as expected?"""

        board = self.config.get('clipster', 'default_selection')
        socket_file = self.config.get('clipster', 'socket_file')
        client_action = "SELECT"
        # Count isn't actually tested here
        count = 99
        self.args.delim = '\0'
        self.args.select = True
        self.args.number = 99
        client = clipster.Client(self.config, self.args)
        # Describe what recv should expect as a return value
        sock = mock_socket.return_value
        sock.recv.side_effect = [json.dumps(self.history[board]).encode('utf-8'), ""]
        # We probably don't need to test for recv, shutdown, close etc, but leave as examples for now
        output = client.output()

        self.assertTrue(mock.call.connect(os.path.join(self.data_dir, socket_file)) in sock.mock_calls)
        self.assertTrue(mock.call.sendall('{}:{}:{}'.format(client_action, board, count).encode('utf-8')) in sock.mock_calls)
        self.assertTrue(mock.call.shutdown(mock.ANY) in sock.mock_calls)
        self.assertTrue(mock.call.recv(mock.ANY) in sock.mock_calls)
        self.assertTrue(mock.call.close() in sock.mock_calls)

        self.assertEqual(output, '\0'.join(self.history[board]))


class DaemonTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.logger = logging.getLogger()
#        cls.logger.level = logging.DEBUG

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        # Read in the config and args defaults
        self.args = clipster.parse_args()
        # 2nd argument is the data dir - usually derived from XDG/ENV
        # Set to an explicit value for testing
        self.data_dir = "/data_dir"
        self.conf_dir = "/conf_dir"
        self.config = clipster.parse_config(self.args, self.data_dir, self.conf_dir)

        # Set up a fake history
        self.history = {"CLIPBOARD": ["ape", "bear\nbear", "cat\ncat\n"], "PRIMARY": ["apple", "banana\nbanana", "clementine\nclementine\n"]}
        self.daemon = clipster.Daemon(self.config)

    def tearDown(self):
        self.history = None

    def test_read_history_file(self):
        """Test that read_history_file correctly reads json from a file."""

        hist_file = self.config.get('clipster', 'history_file')
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=json.dumps(self.history))) as mock_file:
            self.daemon.read_history_file()
        self.assertEqual(self.daemon.boards, self.history)

    def test_ignore_patterns(self):
        """Test that pattern matches aren't added to history."""
        self.config.set('clipster', 'ignore_patterns', 'yes')
        board = 'PRIMARY'
        self.daemon.ignore_patterns = ['^cat$']
        self.daemon.update_history(board, 'cat')
        self.daemon.update_history(board, 'placate')
        self.assertTrue('cat' not in self.daemon.boards[board])
        self.assertTrue('placate' in self.daemon.boards[board])

    @mock.patch('clipster.os')
    @mock.patch('clipster.tempfile.NamedTemporaryFile')
    def test_write_history_file_json(self, mock_tmp, mock_os):
        """Test that write_history_file generates correct json output."""

        # Set the history size to 2 to check the file is correctly truncated
        self.config.set('clipster', 'history_size', "2")
        # Push the test history to the daemon's in-memory history
        self.daemon.boards = self.history
        self.daemon.update_history_file = True
        hist_file = self.config.get('clipster', 'history_file')
        # Fake instantiation of context manager
        mock_file = mock.MagicMock()
        mock_tmp.return_value.__enter__.return_value = mock_file
        self.daemon.write_history_file()
        # Get the json passed to write()
        saved_history = json.loads(mock_file.mock_calls[0][1][0].decode('utf-8'))
        # Check the written history still has same keys
        self.assertEqual(saved_history.keys(), self.history.keys())
        # Check that there are only 2 items in each list
        self.assertTrue(all(len(x) == 2 for x in saved_history.values()))

    def test_read_board(self):
        """Test reading from a previously set clipboard."""
        msg = "clipster test text."
        primary = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
        primary.set_text(msg, -1)
        self.assertEqual(msg, self.daemon.read_board('primary'))

    def test_update_board(self):
        """Test Updating the clipboard."""
        msg = "clipster test text.\n"
        self.daemon.update_board('primary', msg)
        primary = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
        self.assertEqual(msg, primary.wait_for_text())

    def test_remove_history_no_item(self):
        """Test removing an item from the history that isn't there."""
        self.daemon.remove_history('PRIMARY', 'apple')

    def test_remove_history(self):
        """Test removing an item from the history."""
        board = 'PRIMARY'
        self.daemon.boards = self.history
        self.daemon.remove_history(board, 'apple')
        self.assertFalse('apple' in self.daemon.boards[board])

    def test_duplicates_no(self):
        """Test not allowing duplicates in history."""
        self.config.set('clipster', 'duplicates', 'no')
        board = 'PRIMARY'
        self.daemon.update_history(board, 'copy')
        self.daemon.update_history(board, 'copy')
        self.assertTrue(len(self.daemon.boards[board]) == 1)

    def test_duplicates_yes(self):
        """Test allowing duplicates in history."""
        self.config.set('clipster', 'smart_update', '1000')
        self.config.set('clipster', 'duplicates', 'yes')
        board = 'PRIMARY'
        self.daemon.update_history(board, 'copy')
        self.daemon.update_history(board, 'copy')
        self.assertTrue(len(self.daemon.boards[board]) > 1)

    def test_smart_update(self):
        """Test that smart update works from left to right."""
        self.config.set('clipster', 'smart_update', '1')
        board = 'PRIMARY'
        # Select 'forwards'
        self.daemon.update_history(board, 'ye')
        self.daemon.update_history(board, 'yes')
        self.assertTrue(len(self.daemon.boards[board]) == 1)

    def test_smart_update_disable(self):
        """Test that smart update is disabled by setting to 0."""
        self.config.set('clipster', 'smart_update', '0')
        board = 'PRIMARY'
        # Select 'forwards'
        self.daemon.update_history(board, 'ye')
        self.daemon.update_history(board, 'yes')
        self.assertTrue(len(self.daemon.boards[board]) > 1)

    def test_smart_update_backwards(self):
        """Test that smart_update works when selecting from right to left."""
        self.config.set('clipster', 'smart_update', '1')
        board = 'PRIMARY'
        # Select 'backwards'
        self.daemon.update_history(board, 'o')
        self.daemon.update_history(board, 'no')
        self.assertTrue(len(self.daemon.boards[board]) == 1)

    def test_smart_update_limit(self):
        """Test that selection 'extends' greater than smart_update limit are ignored."""
        self.config.set('clipster', 'smart_update', '1')
        board = 'PRIMARY'
        # Extend selection by several chars
        self.daemon.update_history(board, 'short')
        self.daemon.update_history(board, 'shortening')
        self.assertTrue(len(self.daemon.boards[board]) > 1)

    @mock.patch('clipster.socket.socket')
    def test_max_input(self, mock_socket):
        """Test that the max_input limit works."""

        max_input = self.config.getint('clipster', 'max_input')
        header = "SEND:PRIMARY:0:"
        # Set the text to be the same length as max_input
        # so that total length (plus header) exceeds it.
        text = "x" * max_input
        conn = mock_socket.connect
        # Make mock conn.recv simulate bufsize 'trimming'
        conn.recv.side_effect = lambda l: (header + text)[:l]
        # Set up a fake conn fileno and client_msgs dictionary
        conn.fileno.return_value = 0
        self.daemon.client_msgs = {0: []}
        while True:
            if not self.daemon.socket_recv(conn, None):
                break
        text = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY).wait_for_text()
        # check that text length has been trimmed to max_input
        self.assertEqual(len(header) + len(text), max_input)

    def test_sync_selections(self):
        """Test that sync_selections syncs between boards."""
        self.config.set('clipster', 'sync_selections', 'yes')
        text = '100°C'
        self.daemon.update_history('PRIMARY', text)
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.assertEqual(text, clipboard.wait_for_text())

    @mock.patch('clipster.logging.error')
    def test_process_msg_invalid(self, mock_logging):
        """Process an invalid client message."""

        # Set up a mock of some of a socket connection object
        conn = mock.MagicMock()
        conn.fileno.return_value = 1
        self.daemon.client_msgs = {1: "INVALID MESSAGE"}
        self.daemon.process_msg(conn)
        mock_logging.assert_called_with('Invalid message received via socket: %s', 'INVALID MESSAGE')

    @mock.patch('clipster.Daemon.update_board')
    def test_process_msg_update(self, mock_update_board):
        """Process a client message to update a board."""

        # Set up a mock of some of a socket connection object
        conn = mock.MagicMock()
        conn.fileno.return_value = 1

        action = 'SEND'
        board = 'PRIMARY'
        count = '0'
        msg = 'Hello world\n'
        self.daemon.client_msgs = {1: '{}:{}:{}:{}'.format(action, board, count, msg)}
        self.daemon.process_msg(conn)
        mock_update_board.assert_called_with(board, msg)

    @mock.patch('clipster.Daemon.update_board')
    def test_process_msg_output(self, mock_update_board):
        """Process a client message to output a board's contents."""

        # Set up a mock of some of a socket connection object
        conn = mock.MagicMock()
        conn.fileno.return_value = 1
        conn.sendall.return_value = True
        self.daemon.boards = self.history

        action = 'BOARD'
        board = 'PRIMARY'
        count = 1
        self.daemon.client_msgs = {1: '{}:{}:{}'.format(action, board, count)}
        self.daemon.process_msg(conn)
        args, kwargs = conn.sendall.call_args
        msg_list = json.loads(args[0].decode('utf-8'))
        self.assertListEqual(self.history[board][-count:], msg_list)

    def test_process_msg_delete_last(self):
        """Process a client message to delete the last item from a board."""

        # Set up a mock of some of a socket connection object
        conn = mock.MagicMock()
        conn.fileno.return_value = 1
        conn.sendall.return_value = True
        self.daemon.boards = self.history

        action = 'DELETE'
        board = 'PRIMARY'
        board_length = len(self.history[board])
        count = 1
        self.daemon.client_msgs = {1: '{}:{}:{}'.format(action, board, count)}
        self.daemon.process_msg(conn)
        # Board should be one item less
        self.assertEqual(board_length - len(self.history[board]), 1)

    def test_process_msg_delete_pattern_match(self):
        """Process a client message to delete a specific item from a board."""

        # Set up a mock of some of a socket connection object
        conn = mock.MagicMock()
        conn.fileno.return_value = 1
        conn.sendall.return_value = True
        self.daemon.boards = self.history

        action = 'DELETE'
        board = 'PRIMARY'
        count = 1
        pattern = "apple"
        board_length = len(self.history[board])
        self.daemon.client_msgs = {1: '{}:{}:{}:{}'.format(action, board, count, pattern)}
        self.daemon.process_msg(conn)
        # Board should be one item less
        self.assertEqual(board_length - len(self.history[board]), 1)

    def test_process_msg_delete_pattern_no_match(self):
        """Process a client message to delete a nonexistent item from a board."""

        # Set up a mock of some of a socket connection object
        conn = mock.MagicMock()
        conn.fileno.return_value = 1
        conn.sendall.return_value = True
        self.daemon.boards = self.history

        action = 'DELETE'
        board = 'PRIMARY'
        count = 1
        pattern = "notinhistory"
        board_length = len(self.history[board])
        self.daemon.client_msgs = {1: '{}:{}:{}:{}'.format(action, board, count, pattern)}
        self.daemon.process_msg(conn)
        # Board should be one item less
        self.assertEqual(board_length, len(self.history[board]))

    def test_process_msg_erase(self):
        """Process a client message to erase a board's contents."""

        # Set up a mock of some of a socket connection object
        conn = mock.MagicMock()
        conn.fileno.return_value = 1
        conn.sendall.return_value = True
        self.daemon.boards = self.history

        action = 'ERASE'
        board = 'PRIMARY'
        count = 1
        self.daemon.client_msgs = {1: '{}:{}:{}'.format(action, board, count)}
        self.daemon.process_msg(conn)
        # Board should be empty
        self.assertEqual(len(self.history[board]), 0)

if __name__ == "__main__":
    unittest.main()
