# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from contextlib import contextmanager
from types import SimpleNamespace

from frappe.database import savepoint


@contextmanager
def assert_raises_with_savepoint(test_case, expected_exception):
	"""Assert an exception while keeping the surrounding test transaction usable."""
	context = SimpleNamespace(exception=None)
	with savepoint():
		try:
			yield context
		except Exception as exception:
			context.exception = exception
			raise

	if context.exception is None:
		test_case.fail(f"{expected_exception.__name__} not raised")
	if not isinstance(context.exception, expected_exception):
		raise context.exception
