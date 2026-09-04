# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from erpnext.edi.doctype.code_list.code_list import _version_key
from erpnext.tests.utils import ERPNextTestSuite


class TestCodeList(ERPNextTestSuite):
	def test_version_key_orders_integers_and_iso_dates(self):
		"""Integer and ISO date versions must both order correctly, unlike a lexical sort."""
		self.assertEqual(sorted(["10", "3", None, "9"], key=_version_key), [None, "3", "9", "10"])
		self.assertEqual(
			sorted(["2020-11-05", "2019-12-31", "2020-01-01"], key=_version_key),
			["2019-12-31", "2020-01-01", "2020-11-05"],
		)
