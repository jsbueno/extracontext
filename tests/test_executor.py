import threading
import time
from collections import deque

import pytest

from extracontext import ContextPreservingExecutor


consume = deque(maxlen=0).extend


def test_executor_preserces_context:

    ctx = ContextPreservingExecutor(1)
    ...
    # [WIP]
