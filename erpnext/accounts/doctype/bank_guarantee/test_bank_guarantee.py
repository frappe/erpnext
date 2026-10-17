# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from frappe.utils import flt

from erpnext.accounts.doctype.bank_guarantee.bank_guarantee import get_voucher_details
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.tests.utils import ERPNextTestSuite


class TestBankGuarantee(ERPNextTestSuite):
	"""Bank Guarantee records a guarantee issued/received against a customer or
	supplier. validate() needs a party; on_submit() needs the bank details filled in."""

	def test_get_voucher_details_for_receiving(self):
		so = make_sales_order()
		details = get_voucher_details("Receiving", so.name)
		self.assertEqual(details.customer, so.customer)
		self.assertEqual(flt(details.grand_total), flt(so.grand_total))
