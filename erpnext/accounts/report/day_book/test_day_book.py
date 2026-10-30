import frappe
from frappe.utils import today

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.day_book.day_book import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestDayBook(ERPNextTestSuite):
	def test_one_row_per_voucher_with_ledger_lines(self):
		sinv = create_sales_invoice(rate=500)
		payment = get_payment_entry(sinv.doctype, sinv.name).save().submit()

		filters = frappe._dict(company=sinv.company, from_date=today(), to_date=today(), detailed=1)
		_columns, data = execute(filters)
		vouchers = {row["voucher_no"]: row for row in data if not row["indent"]}

		self.assertEqual(vouchers[sinv.name]["particulars"], sinv.customer_name)
		self.assertEqual(vouchers[sinv.name]["debit"], sinv.base_grand_total)
		self.assertEqual(vouchers[payment.name]["credit"], payment.base_paid_amount)

		lines = [row for row in data if row.get("parent_voucher") == vouchers[sinv.name]["voucher"]]
		self.assertEqual(sum(row["debit"] or 0 for row in lines), sum(row["credit"] or 0 for row in lines))

		filters.voucher_type = "Payment Entry"
		_columns, data = execute(filters)
		self.assertEqual({row["voucher_type"] for row in data if not row["indent"]}, {"Payment Entry"})
