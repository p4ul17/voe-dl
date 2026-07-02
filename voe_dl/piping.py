import sys
from io import StringIO

# When stdout is piped, buffer all print() output and only emit the
# resolved download link at the end (ported from upstream PR #52 by @Czer0xx)
PIPED = not sys.stdout.isatty()
if PIPED:
    sys.stdout_real = sys.stdout
    sys.stdout = StringIO()


def flush_piped_link(url):
    """Restore the real stdout and write only the resolved link, for piped usage."""
    sys.stdout = sys.stdout_real
    sys.stdout.write(url + "\n")
    sys.stdout.flush()
