import os.path as op
from collections import deque

from pyndemic.core.context import (ContextRegistrationMeta, unregister_context,
                                   ContextNotFoundError)
from pyndemic import config


SETTINGS_LOCATION = op.join(op.dirname(__file__), 'test_settings.cfg')


class MockController(metaclass=ContextRegistrationMeta,
                     ctx_name='controller'):
    """Help Controller-like class with "signals" and "_ctx" attributes."""
    def __init__(self):
        self.signals = deque()
        self.settings = config.get_settings(SETTINGS_LOCATION, refresh=True)