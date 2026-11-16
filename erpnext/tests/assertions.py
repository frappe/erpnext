# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from contextlib import contextmanager
from types import SimpleNamespace

import frappe
from frappe.database import savepoint


def assert_post_only(test_case, *functions):
	"""Assert each whitelisted function rejects GET, so a cross-site link cannot call it."""
	for fn in functions:
		test_case.assertEqual(
			frappe.allowed_http_methods_for_whitelisted_func.get(fn), ("POST",), fn.__qualname__
		)


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
