#!/usr/bin/python3

# OpenMPT ANSI Syntax Highlighting (Python version)
# by cs127 @ https://cs127.github.io
# https://github.com/cs127/mptsh-python
#
#
# version 0.0.0 (port of Java version 0.2.1)
# 2022-11-23
#
#
# Requirements:
#
# * pyperclip (for reading/writing to the clipboard)
#   You can still read from STDIN and write to STDOUT without pyperclip.



import os, sys, re
from enum import IntFlag, auto



HEADER = 'ModPlug Tracker '
FORMATS_M = ['MOD', ' XM']
FORMATS_S = ['S3M', ' IT', 'MPT']
DEFAULT_COLORS = [7, 5, 4, 2, 6, 3, 1, 7]
LINEBREAK = os.linesep

HELP_TEXT = '''
Usage: [EXEC] [OPTIONS] [COLORS]

Options:
-h | --help         Help (display this screen)
-i | --stdin        Read input from STDIN instead of clipboard
-o | --stdout       Write output to STDOUT instead of clipboard
-d | --markdown     Automatically wrap output in Markdown code block (for Discord)
-r | --reverse      Reverse mode - removes syntax highlighting instead of adding

Using auto-markdown does nothing if reverse mode is enabled.

Colors:
X,X,X,X,X,X,X,X  Each value from 0 to 15 (Discord only supports 0 to 7)
format: Default,Note,Instrument,Volume,Panning,Pitch,Global,ChannelSeparator
if not provided: 7,5,4,2,6,3,1,7
'''


class CLIOption(IntFlag):
    HELP          = auto()
    USE_STDIN     = auto()
    USE_STDOUT    = auto()
    AUTO_MARKDOWN = auto()
    REVERSE_MODE  = auto()



def get_cli_options(args):
    options = 0
    for arg in args:
        if arg.startswith('-'):
            if not arg.startswith('--'):
                for c in range(1, len(arg)):
                    match arg[c]:
                        case 'h': options |= CLIOption.HELP
                        case 'i': options |= CLIOption.USE_STDIN
                        case 'o': options |= CLIOption.USE_STDOUT
                        case 'd': options |= CLIOption.AUTO_MARKDOWN
                        case 'r': options |= CLIOption.REVERSE_MODE
            else:
                match arg:
                    case '--help':     options |= CLIOption.HELP
                    case '--stdin':    options |= CLIOption.USE_STDIN
                    case '--stdout':   options |= CLIOption.USE_STDOUT
                    case '--markdown': options |= CLIOption.AUTO_MARKDOWN
                    case '--reverse':  options |= CLIOption.REVERSE_MODE
    return options

def get_sgr_code(color):
    n = color + (30 if color < 8 else 82)
    return '\u001B[%dm'%n

def get_note_color(c):
    return 1 if c >= 'A' and c <= 'G' else 0

def get_instrument_color(c):
    return 2 if c >= '0' else 0

def get_volume_cmd_color(c):
    color = 0
    match c:
        case 'a' | 'b' | 'c' | 'd' | 'v': color = 3 # Volume
        case 'l' | 'p' | 'r'            : color = 4 # Panning
        case 'e' | 'f' | 'g' | 'h' | 'u': color = 5 # Pitch
    return color

def get_effect_cmd_color(c, f):
    color = 0
    if f in FORMATS_S: # S3M/IT/MPTM
        match c:
            case 'D' | 'K' | 'L' | 'M' | 'N' | 'R'      : color = 3 # Volume
            case 'P' | 'X' | 'Y'                        : color = 4 # Panning
            case 'E' | 'F' | 'G' | 'H' | 'U' | '+' | '*': color = 5 # Pitch
            case 'A' | 'B' | 'C' | 'T' | 'V' | 'W'      : color = 6 # Global
    elif f in FORMATS_M: # MOD/XM
        match c:
            case '5' | '6' | '7' | 'A' | 'C': color = 3 # Volume
            case '8' | 'P' | 'Y'            : color = 4 # Panning
            case '1' | '2' | '3' | '4' | 'X': color = 5 # Pitch
            case 'B' | 'D' | 'F' | 'G' | 'H': color = 6 # Global
    return color



# Find the first non-option command-line argument
colors_arg_index = 1
while colors_arg_index < len(sys.argv):
    if not sys.argv[colors_arg_index].startswith('-'): break
    colors_arg_index += 1
    if sys.argv[colors_arg_index-1] == '--': break

# Get command-line options
options = get_cli_options(sys.argv[:colors_arg_index])
help          = options & CLIOption.HELP
use_stdin     = options & CLIOption.USE_STDIN
use_stdout    = options & CLIOption.USE_STDOUT
auto_markdown = options & CLIOption.AUTO_MARKDOWN
reverse       = options & CLIOption.REVERSE_MODE

# Show help (and then exit) if the help option is provided
if help:
    print(HELP_TEXT)
    os._exit(os.EX_OK)

# Use the first non-option command-line argument as the list of colors
colors = [0] * len(DEFAULT_COLORS)
try:
    colors_str = sys.argv[colors_arg_index].split(',')
    for c in range(len(colors)):
        colors[c] = int(colors_str[c])
        if colors[c] not in range(16): raise Exception('Invalid color ' + colors[c])
except:
    if not use_stdout:
        print('Colors not provided properly. Default colors will be used.')
    colors = DEFAULT_COLORS.copy()

# Read clipboard/STDIN
if not use_stdin or not use_stdout: import pyperclip
try: data = ''.join(sys.stdin.readlines()) if use_stdin else pyperclip.paste()
except:
    print('Unable to read clipboard.')
    os._exit(1)

# Try to get the module format and check if the data is valid OpenMPT pattern data
try:
    f = data[len(HEADER):len(HEADER)+3]
    if not data.startswith(HEADER) or f not in FORMATS_M and f not in FORMATS_S: raise Exception()
except:
    print('%s does not contain OpenMPT pattern data.'%('STDIN' if use_stdin else 'Clipboard'))
    os._exit(2)

# Remove colors if the input is already syntax-highlighted
data = re.sub('\u001B\\[\\d+(;\\d+)*m', '', data)

# Add colors if reverse mode is not enabled
result = ''
if not reverse:
    rel_pos = -1
    color = -1
    previous_color = -1
    for p in range(len(data)):
        c = data[p]
        if c == '|': rel_pos = 0
        if rel_pos == 0: color = colors[7]                          # Channel separator
        if rel_pos == 1: color = colors[get_note_color(c)]          # Note
        if rel_pos == 4: color = colors[get_instrument_color(c)]    # Instrument
        if rel_pos == 6: color = colors[get_volume_cmd_color(c)]    # Volume command
        if rel_pos >= 9:                                            # Effect command(s)
            if not rel_pos % 3: color = colors[get_effect_cmd_color(c, f)]
            if rel_pos % 3 and c == '.' and data[p-(rel_pos%3)] != '.': c = '0'
        if not c.isspace():
            if color != previous_color: result += get_sgr_code(color)
            previousColor = color
        result += c
        if rel_pos >= 0: rel_pos += 1
else: result = data

# Wrap in code block for Discord if specified
if auto_markdown and not reverse: result = '```ansi' + LINEBREAK + result + '```'

# Write to clipboard/STDOUT
if use_stdout: print(result)
else: pyperclip.copy(result)
