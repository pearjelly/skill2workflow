"""Owned HTTP fixtures with prompt shutdown, without changing runtime servers.

The stdlib's half-second idle polling interval dominates many short tests.
Only these test subclasses use a 10 ms default; explicit intervals and actual
HTTP request handling, shutdown and close semantics remain inherited.
"""

from http.server import HTTPServer as _HTTPServer
from http.server import ThreadingHTTPServer as _ThreadingHTTPServer


class _FixturePolling:
    def serve_forever(self, poll_interval=0.01):
        return super().serve_forever(poll_interval=poll_interval)


class HTTPServer(_FixturePolling, _HTTPServer):
    pass


class ThreadingHTTPServer(_FixturePolling, _ThreadingHTTPServer):
    pass
