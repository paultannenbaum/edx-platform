"""
General testing utilies.
"""

from markupsafe import escape
from mock import Mock


class XssTestMixin(object):
    """
    Mixin for testing XSS vulnerabilities.
    """

    def assert_xss(self, response, xss_content):
        """Assert that `xss_content` is not present in the content of
        `response`, and that its escaped version is present. Uses the
        same `markupsafe.escape` function as Mako templates.

        Args:
          response (Response): The HTTP response
          xss_content (str): The Javascript code to check for.

        Returns:
          None

        """
        self.assertContains(response, escape(xss_content))
        self.assertNotContains(response, xss_content)


class MockSignalHandlerMixin(object):
    """Mixin for testing sending of signals."""

    handlers = {}

    def setup_signal_handler(self, signal):
        """Install a signal handler.

        Args:
          signal (Signal): The signal to register a test handler for.

        Returns:
          None
        """
        def handler(*args, **kwargs):
            """No-op signal handler."""
            pass
        mock_handler = Mock(spec=handler)
        signal.connect(mock_handler)
        self.handlers[signal] = mock_handler

    def assert_signal_sent(self, signal, *args, **kwargs):
        """Assert that `signal` was sent with the correct arguments. Since
        Django calls signal handlers with the signal as an argument, it is
        added to `kwargs`.

        Args:
          signal (Signal): The signal which should have been sent.
          *args, **kwargs: The arguments which should have been passed
            along with the signal.

        Returns:
          None
        """
        self.handlers[signal].assert_called_with(*args, **dict(kwargs, signal=signal))
