from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.templates.pages.order import get_payment_details


class TestOrder(FrappeTestCase):
	@change_settings("Buying Settings", {"show_pay_button": 0})
	def test_buying_pay_button_setting_skips_selling_documents(self):
		so = make_sales_order()
		po = create_purchase_order()

		with patch.object(frappe, "get_installed_apps", return_value=["frappe", "erpnext", "payments"]):
			self.assertEqual(get_payment_details(so), (True, so.grand_total))
			self.assertEqual(get_payment_details(po), (False, 0))
