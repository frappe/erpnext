# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.utils import get_fiscal_year
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.regional.report.irs_1099.irs_1099 import execute, get_street_address_html
from erpnext.tests.utils import ERPNextTestSuite

US_COMPANY = "_Test Company 1"


class TestIRS1099StreetAddress(ERPNextTestSuite):
	def test_street_address_prefers_postal(self):
		"""The original query cross-joined Address with no join predicate, so its
		`ORDER BY address_type='Postal' DESC` sorted on an arbitrary cross-joined row and never
		controlled which link.parent (Address) was returned. The conversion joins address.name ==
		link.parent so the Postal/Billing preference actually applies; a `link.parent` tie-break keeps
		the LIMIT-1 pick deterministic across engines when several addresses share the top type."""
		party = "_Test 1099 Address Supplier"
		if not frappe.db.exists("Supplier", party):
			frappe.get_doc(
				{"doctype": "Supplier", "supplier_name": party, "supplier_group": "_Test Supplier Group"}
			).insert(ignore_permissions=True)

		def mk_addr(title, address_type, line1):
			frappe.get_doc(
				{
					"doctype": "Address",
					"address_title": title,
					"address_type": address_type,
					"address_line1": line1,
					"city": "Testville",
					"country": "United States",
					"links": [{"link_doctype": "Supplier", "link_name": party}],
				}
			).insert(ignore_permissions=True)

		mk_addr("_Test 1099 Billing", "Billing", "1 Billing St")
		mk_addr("_Test 1099 Postal", "Postal", "9 Postal Rd")

		street, _city_state = get_street_address_html("Supplier", party)
		# the Postal address must win over the Billing one (deterministically, on both engines)
		self.assertIn("9 Postal Rd", street)
		self.assertNotIn("1 Billing St", street)


class TestIRS1099(ERPNextTestSuite):
	def test_total_payments_are_net_payments(self):
		supplier = make_1099_supplier()
		pi = make_us_purchase_invoice(supplier, qty=10, rate=100)
		pay(pi, 600)
		pay(pi, 300).cancel()

		debit_note = make_return_doc("Purchase Invoice", pi.name)
		debit_note.items[0].qty = -1
		debit_note.submit()

		refund = get_payment_entry("Purchase Invoice", debit_note.name, bank_account="Cash - _TC1")
		refund.paid_amount = refund.received_amount = 50
		refund.references = []
		refund.reference_no, refund.reference_date = "_Test Refund", nowdate()
		refund.submit()

		self.assertEqual(get_total_payments(supplier), 550)

	def test_company_permission(self):
		frappe.permissions.add_user_permission("Company", "_Test Company", "test2@example.com")
		frappe.get_doc("User", "test2@example.com").add_roles("Accounts Manager")

		with self.set_user("test2@example.com"):
			self.assertRaises(frappe.PermissionError, get_total_payments, "_Test Supplier")


def make_1099_supplier() -> str:
	supplier = frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": "_Test 1099 Supplier " + frappe.generate_hash(length=6),
			"supplier_group": "_Test Supplier Group",
			"irs_1099": 1,
		}
	).insert()
	return supplier.name


def make_us_purchase_invoice(supplier: str, **args):
	return make_purchase_invoice(
		company=US_COMPANY,
		supplier=supplier,
		currency="USD",
		item="_Test Non Stock Item",
		warehouse="Stores - _TC1",
		cost_center="Main - _TC1",
		expense_account="Cost of Goods Sold - _TC1",
		**args,
	)


def pay(pi, amount: float):
	payment = get_payment_entry("Purchase Invoice", pi.name, party_amount=amount, bank_account="Cash - _TC1")
	payment.reference_no, payment.reference_date = "_Test Payment", nowdate()
	return payment.submit()


def get_total_payments(supplier: str) -> float:
	filters = {"company": US_COMPANY, "fiscal_year": get_fiscal_year(nowdate(), company=US_COMPANY)[0]}
	_columns, data = execute(filters)
	return next((row.payments for row in data if row.supplier == supplier), 0)
