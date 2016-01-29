# Clipster

Clipster is a simple clipboard manager, written in `Python` (2 or 3). It aims to be lightweight, have a small set of non-core dependencies (`Gtk+`), and is designed to interact well with tiling and keyboard-based window managers. It uses selection events, rather than polling, and offers both command-line and GUI interaction with the clipboard.

Clipster has 2 modes of operation - `daemon`, which handles clipboard events and maintains a history, and `client`, which requests clipboard history from, and pushes new items to, the daemon.


## Installation

You will need the python bindings for the gobject introspection libraries. These are provded by the `python-gi` package on debian-based systems, or by the `pygobject3` package on redhat-based systems.

To install Clipster, simply download the clipster script from this repository and save it somewhere in your path.


## Configuration

### Command-line options

```
~$ clipster -h
usage: clipster [-h] [-f CONFIG] [-p] [-c] [-d] [-s]

Clipster clipboard manager.

optional arguments:
  -h, --help            show this help message and exit
  -f CONFIG, --config CONFIG
                        Path to config file.
  -l LOG_LEVEL, --log_level LOG_LEVEL
                        Set log level: DEBUG, INFO (default), WARNING, ERROR,
                        CRITICAL
  -p, --primary         Query, or write STDIN to, the PRIMARY clipboard.
  -c, --clipboard       Query, or write STDIN to, the CLIPBOARD clipboard.
  -d, --daemon          Launch the daemon.
  -s, --select          Launch the clipboard history selection window.

```


### Config file

Clipster looks for its configuration file (and other resources) in `$HOME/.clipster` by default, but this can be changed using the `-f` option.

The config options, and their default values, are shown below. Note the `%()s` syntax can be used to re-use an existing config option's value elsewhere.

You can create a config file containing only some of the options, and the rest will be derived from defaults.


``` 
[clipster]
# 'root' directory for clipster resources (defaults to $HOME/.clipster)
clipster_dir = /path/to/clipster/resources

# Default selection (if no -p of -c given on command-line): can be PRIMARY or CLIPBOARD
default_selection = PRIMARY

# full path to the clipster history file (JSON)
# Maximum file size is: 'history_size * max_input * 2' (defaults: 10MB)
history_file = %(clipster_dir)s/history

# Number of items to save in the history file for each selection.
history_size = 200

# Time in seconds to flush history to disk, if changed
# Set to 0 to only write history file on (clean) exit
history_update_interval = 60

# Write history file immediately after selection changes?
# If yes, disables history_update_interval
write_on_change = no

# Full path to the clipster socket file
socket_file = %(clipster_dir)s/clipster_sock

# Full path to the clipster pid file
pid_file = %(clipster_dir)s/clipster.pid

# Maximum length for new clipboard items
max_input = 50000

# Number of rows of clipboard content to show in the selection widget before truncating
# Set to a high number to avoid truncation
row_height = 3

# Allow duplicates in the clipboard (if set to no, the earlier entry will be removed)
duplicates = no

# smart_update tries to be clever about small changes to the selection, and only adds
# to the history if the number of characters added or removed is greater than it's value.
# for example, if set to 2: the latest clipboard entry catch, would be replaced by any of:
# cat, catc, catchy, catcher, but not ca or catchers.
# Defaults to 1, as some applications update the clipboard by continually adding new
# items with a single character added or removed each time.
# Set to 0 to disable.
smart_update = 1

# Extract uris from the selection text and add them to the default clipboard
extract_uris = yes

# Extract emails from the selection text and add them to the default clipboard
extract_emails = yes


```

## Using Clipster

### Launch the daemon

The first step is to launch the Clipster daemon:

``` bash
~$ clipster -d
```

This can be run as a background task on session start.

For debugging, use the `-l` option:

``` bash
~$ clipster -d -l DEBUG
```

### Using the client

The client will use the value of `default_selection` from the config file to decide which selection to read from - this can be overridden using the `-p` and `-c` options.


To get the latest entry in the clipboard:

``` bash
~$ clipster [-p|-c]
```

To add some text to the clipboard:

``` bash
~$ echo "hello world" | clipster [-p|-c]
```

To launch the clipboard selection dialog box:

``` bash
~$ clipster -s [-p|-c]
```

### Selection dialog

The dialog box can be used to select an item from the clipboard history - either `Arrow Keys` and `Return` or mouse (double-click) can be used to select an item. Pressing `Esc` will close the dialog.

Items containing multiple lines will be truncated based on the `row_height` config value.


## WM Integration

It's easy to integrate clipster into an existing window manager by binding clipster commands to keyboard shortcuts.

For example, in i3 (my WM of choice) I have the following in my .i3/config file:

```
# Start clipster daemon
exec --no-startup-id clipster -d

# shortcut to selection widget (primary)
bindsym $mod+c exec clipster -sp

```

## Bugs & Improvements

I'm happy to receive any bug reports, pull requests, suggestions for features or other improvements - with the following caveats:

* Clipster should remain driven by the command-line and keyboard - no GUI-only or mouse-only features.

* No extra 3rd party dependencies (unless they are ones found in the core of most distros).

* No requirement for packaging for installation (I'm happy to accept specfiles, debian packaging files etc - but you must always be able to just download and run Clipster if you want).
