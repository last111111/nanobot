"""Test helpers and environment shims."""

from __future__ import annotations

import sys
import types


def _noop(*args, **kwargs):
    return None


try:
    import loguru  # noqa: F401
except ModuleNotFoundError:
    logger = types.SimpleNamespace()
    logger.debug = _noop
    logger.info = _noop
    logger.warning = _noop
    logger.error = _noop
    logger.exception = _noop
    logger.critical = _noop
    logger.bind = lambda *args, **kwargs: logger
    logger.opt = lambda *args, **kwargs: logger
    sys.modules["loguru"] = types.SimpleNamespace(logger=logger)


try:
    import litellm  # noqa: F401
except ModuleNotFoundError:
    async def _acompletion(*args, **kwargs):
        raise RuntimeError("litellm stub should not be used for real completions in tests")

    sys.modules["litellm"] = types.SimpleNamespace(
        acompletion=_acompletion,
        api_base=None,
        suppress_debug_info=True,
        drop_params=True,
    )
