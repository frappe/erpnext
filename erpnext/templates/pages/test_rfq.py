# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.buying.doctype.request_for_quotation.test_request_for_quotation import (
	make_request_for_quotation,
)


class TestRFQPage(FrappeTestCase):
	def test_draft_rfq_page_is_not_permitted(self):
		from erpnext.templates.pages.rfq import get_context

		rfq = make_request_for_quotation(do_not_submit=True)
		with patch.dict(frappe.form_dict, {"doctype": "Request for Quotation", "name": rfq.name}):
			self.assertRaises(frappe.PermissionError, get_context, frappe._dict())
