"""Smoke tests: every project module imports cleanly under the conftest stubs.

This catches breakage from circular imports, missing names, or hardware-side
imports that escape the stubs."""


def test_radio_state_machine_imports():
  import radio_state_machine  # noqa: F401


def test_display_state_imports():
  import display_state  # noqa: F401


def test_main_thread_imports():
  import main_thread  # noqa: F401


def test_menu_thread_imports():
  import menu_thread  # noqa: F401


def test_unlocker_imports():
  import unlocker  # noqa: F401


def test_activity_timeout_thread_imports():
  import activity_timeout_thread  # noqa: F401


def test_vigie_thread_imports():
  import vigie_thread  # noqa: F401


def test_user_input_listener_imports():
  import user_input_listener  # noqa: F401


def test_graceful_killer_singleton():
  import graceful_killer
  assert hasattr(graceful_killer, 'killer')
  assert hasattr(graceful_killer.killer, 'kill_event')
  assert hasattr(graceful_killer.killer, 'wait')
