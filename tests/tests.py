#!/usr/bin/python

import unittest
import os
import errno
import logging
import json
from gi.repository import Gtk, Gdk

# Uses a symlink - otherwise we're into imp/importlib py-ver hell
import clipster
try:
    from unittest import mock
except ImportError:
    # py 2.x
    import mock


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
        cls.args = clipster.parse_args(None)
        # 2nd argument is the data dir - usually derived from XDG/ENV
        # Set to an explicit value for testing
        cls.data_dir = "/data_dir"
        cls.config = clipster.parse_config(cls.args, cls.data_dir)

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
        self.client = clipster.Client(self.config, self.args)
        self.client.client_update(client_action)
        self.client.sock.connect.assert_called_with(os.path.join(self.data_dir, socket_file))
        self.client.sock.sendall.assert_called_with('{}:{}:0:'.format(client_action,
                                                                      board).encode('utf-8'))

    @mock.patch('clipster.socket.socket')
    def test_client_output(self, mock_socket):
        """Does the client connect, send and receive data as expected?"""

        board = self.config.get('clipster', 'default_selection')
        socket_file = self.config.get('clipster', 'socket_file')
        client_action = "BOARD"
        # Count isn't actually tested here
        count = 99
        self.args.nul = '\x00'
        client = clipster.Client(self.config, self.args)
        # Describe what recv should expect as a return value
        client.sock.recv.side_effect = [json.dumps(self.history[board]).encode('utf-8'), ""]
        # We probably don't need to test for recv, shutdown, close etc, but leave as examples for now
        output = client.client_output(client_action, count)
        client.sock.connect.assert_called_with(os.path.join(self.data_dir, socket_file))
        client.sock.sendall.assert_called_with('{}:{}:{}:'.format(client_action,
                                                                  board, count).encode('utf-8'))
        client.sock.shutdown.assert_called_with(mock.ANY)
        client.sock.recv.assert_called_with(mock.ANY)
        client.sock.close.assert_called_with()

        self.assertEqual(output, self.args.nul.join(self.history[board]))


class DaemonTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Read in the config and args defaults
        cls.args = clipster.parse_args(None)
        # 2nd argument is the data dir - usually derived from XDG/ENV
        # Set to an explicit value for testing
        cls.data_dir = "/data_dir"
        cls.config = clipster.parse_config(cls.args, cls.data_dir)

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        # Set up a fake history
        self.history = {"CLIPBOARD": ["ape", "bear\nbear", "cat\ncat\n"], "PRIMARY": ["apple", "banana\nbanana", "clementine\nclementine\n"]}
        self.daemon = clipster.Daemon(self.config)


    def tearDown(self):
        self.history = None

    def test_read_history_file(self):
        """Test that read_history_file correctly reads json from a file."""

        hist_file = self.config.get('clipster', 'history_file')
        with mock.patch("builtins.open", mock.mock_open(read_data=json.dumps(self.history))) as mock_file:
            self.daemon.read_history_file()
        self.assertEqual(self.daemon.boards, self.history)

    @mock.patch('clipster.os')
    @mock.patch('clipster.tempfile.mkstemp')
    def test_write_history_file_json(self, mock_mkstemp, mock_os):
        """Test that write_history_file generates correct json output."""

        # Set the history size to 2 to check the file is correctly truncated
        self.config.set('clipster', 'history_size', "2")
        # Push the test history to the daemon's in-memory history
        self.daemon.boards = self.history
        self.daemon.update_history_file = True
        hist_file = self.config.get('clipster', 'history_file')
        # Fake return of fd and fname for mkstemp to succeed
        mock_mkstemp.return_value = (1, "test")
        self.daemon.write_history_file()
        args, kwargs = mock_os.write.call_args
        saved_history = json.loads(args[1].decode('utf-8'))
        # Check the history still has same keys
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

    def test_process_msg_invalid(self):
        """Process an invalid client message."""

        # Set up a mock of some of a socket connection object
        conn = mock.MagicMock()
        conn.fileno.return_value = 1

        self.daemon.client_msgs = {1: "INVALID MESSAGE"}
        with self.assertRaises(clipster.ClipsterError):
            self.daemon.process_msg(conn)

    @mock.patch('clipster.Daemon.update_board')
    def test_process_msg_update(self, mock_update_board):
        """Process a client message to update a board."""

        # Set up a mock of some of a socket connection object
        conn = mock.MagicMock()
        conn.fileno.return_value = 1

        action = 'BOARD'
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
        self.daemon.client_msgs = {1: '{}:{}:{}:'.format(action, board, count)}
        self.daemon.process_msg(conn)
        args, kwargs = conn.sendall.call_args
        msg_list = json.loads(args[0].decode('utf-8'))
        self.assertListEqual(self.history[board][-count:], msg_list)


if __name__ == "__main__":
    unittest.main()
