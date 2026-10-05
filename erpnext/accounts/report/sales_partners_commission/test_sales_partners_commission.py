# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.sales_partners_commission.sales_partners_commission import execute
from erpnext.selling.doctype.customer.test_customer import make_customer
from erpnext.tests.utils import ERPNextTestSuite


class TestSalesPartnersCommission(ERPNextTestSuite):
	def setUp(self):
		self.sales_partner = (
			frappe.get_doc(
				{
					"doctype": "Sales Partner",
					"partner_name": f"_Test Partner {frappe.generate_hash(length=6)}",
					"territory": "_Test Territory",
					"commission_rate": 10,
				}
			)
			.insert()
			.name
		)

	def make_invoice(self, customer: str, rate: float):
		invoice = create_sales_invoice(customer=customer, rate=rate, do_not_save=1)
		invoice.sales_partner = self.sales_partner
		invoice.commission_rate = 10
		return invoice.insert().submit()

	def get_partner_row(self) -> dict:
		return next(row for row in execute()[1] if row["sales_partner"] == self.sales_partner)

	def test_user_sees_commission_on_permitted_customers_only(self):
		self.make_invoice("_Test Customer", 1000)
		self.make_invoice(make_customer("_Test Customer2"), 5000)
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"{frappe.generate_hash(length=10)}@example.com",
				"first_name": "Sales Partners Commission Test",
				"send_welcome_email": 0,
				"roles": [{"role": "Accounts User"}],
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user.name,
				"allow": "Customer",
				"for_value": "_Test Customer",
			}
		).insert(ignore_permissions=True)

		frappe.set_user(user.name)
		try:
			row = self.get_partner_row()
		finally:
			frappe.set_user("Administrator")

		self.assertEqual((row["invoiced_amount"], row["total_commission"]), (1000, 100))
