#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Protocol helpers for multiline sh-style-quoted blocks.

Blocks are formatted as lines, separated by newline characters, each
containing one or more quoted words.  The block ends at the first line
containing zero words.

For example:
   this is a line
   so "is this
stuff"
   this 'also' is a "'line'"
   this\ is\ one\ word
   ""
   still going

Parses as follows:
   [['this', 'is', 'a', 'line'],
    ['so', 'is this\nstuff'],
    ['this', 'also', 'is', 'a', "'line'"],
    ['this is one word'],
    [''],
    ['still', 'going']]

The net result is a human-friendly protocol that can be used for many
purposes.
"""
__author__ = 'apenwarr@google.com (Avery Pennarun)'


import bup.shquote
import mainloop


class QuotedBlockProtocol(object):
  """Implement the QuotedBlock protocol.

  You should call GotData() every time you receive incoming data.

  Calls a callback function with an array of lines at the end of each block.
  The callback function returns a list that is then quoted and returned
  from GotData().

  Try using QuotedBlockStreamer for a wrapper that ties this into a mainloop.
  """

  def __init__(self, handle_lines_func):
    """Initialize a QuotedBlockProtocol instance.

    Args:
      handle_lines_func: called as handle_lines_func(lines) at the end of
        each incoming block.  Returns a list of lines to send back.
    """
    self.handle_lines_func = handle_lines_func
    self.partial_line = ''
    self.lines = []

  def GotData(self, data):
    """Call this method every time you receive incoming bytes.

    It will call the handle_lines_func at the end of a block.  When this
    function returns non-None, it will be an encoded block string you should
    send back to the remote end.

    This function knows how to handle lines that contain a quoted newline
    character.  It merges the two lines into a single one and then calls
    self.GotLine().

    Args:
      data: a string of bytes you received from the remote.
    Returns:
      None or a string that should be returned to the remote.
    """
    line = self.partial_line + data
    #pylint: disable-msg=W0612
    firstchar, word = bup.shquote.unfinished_word(line)
    if word:
      self.partial_line = line
    else:
      self.partial_line = ''
      return self.GotLine(line)

  def GotLine(self, line):
    """Call this method every time you receive a parseable line of data.

    Most of the time you will call GotData() instead.  Only use this method
    if you're absolutely sure the line does not have any unfinished quoted
    sections.

    Args:
      line: a parseable string of bytes you received from the remote.
    Returns:
      None or a string that should be returned to the remote.
    """
    if line.strip():
      # a new line in this block
      parts = bup.shquote.quotesplit(line)
      #pylint: disable-msg=W0612
      self.lines.append([word for offset, word in parts])
    else:
      # blank line means end of block
      lines = self.lines
      self.lines = []
      result = self.handle_lines_func(lines)
      if result is None:
        return None
      else:
        return self.RenderBlock(result)

  def RenderBlock(self, lines):
    """Quote the given lines array back into a parseable string."""
    out = []
    lines = lines or []
    for line in lines:
      line = [str(word) for word in line]
      out.append(bup.shquote.quotify_list(line) + '\r\n')
    out.append('\r\n')
    return ''.join(out)


class QuotedBlockStreamer(object):
  """A simple helper that can be used as the callback to MainLoop.Listen.

  Derive from this class and override ProcessBlock() to change how you want
  to interpret and respond to blocks.  The listener will automatically
  accept incoming connections, and ProcessBlock() will be called
  automatically for each full block received from the remote.  It should
  return the lines that should be sent back to the remote.  We send back
  the lines automatically using tornado.IOStream.

  Example:
      loop = mainloop.MainLoop()
      loop.ListenUnix('/tmp/cwmpd.sock', QuotedBlockStreamer)
      loop.Start()
  """

  def __init__(self, sock, address):
    """Initialize a QuotedBlockStreamer.

    Args:
      sock: the socket provided by MainLoop.Listen
      address: the address provided by MainLoop.Listen
    """
    self.sock = sock
    self.address = address
    qb = QuotedBlockProtocol(self.ProcessBlock)
    mainloop.LineReader(sock, address, qb.GotData)

  def ProcessBlock(self, lines):
    """Redefine this function to respond to incoming requests how you want."""
    print 'lines: %r' % (lines,)
    return [['RESPONSE:']] + lines + [['EOR']]


def main():
  loop = mainloop.MainLoop()
  loop.ListenInet6(('', 12999), QuotedBlockStreamer)
  loop.ListenUnix('/tmp/cwmpd.sock', QuotedBlockStreamer)
  print 'hello'
  loop.Start()


if __name__ == '__main__':
  main()
