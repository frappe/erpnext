import frappe
import frappe.defaults
import unittest
from frappe.utils import today, getdate, add_days
from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

class TestAccountsReceivable(unittest.TestCase):
	def test_accounts_receivable(self):
		frappe.db.sql("delete from `tabSales Invoice` where company='_Test Company 2'")
		frappe.db.sql("delete from `tabGL Entry` where company='_Test Company 2'")

		filters = {
			'company': '_Test Company 2',
			'based_on_payment_terms': 1
		}

		name = make_sales_invoice()
		report = execute(filters)

		expected_data = [[100,30], [100,50], [100,20]]

		self.assertEqual(expected_data[0], report[1][0][7:9])
		self.assertEqual(expected_data[1], report[1][1][7:9])
		self.assertEqual(expected_data[2], report[1][2][7:9])

		make_payment(name)
		report = execute(filters)

		expected_data_after_payment = [[100,50], [100,20]]

		self.assertEqual(expected_data_after_payment[0], report[1][0][7:9])
		self.assertEqual(expected_data_after_payment[1], report[1][1][7:9])

		make_credit_note(name)
		report = execute(filters)

		expected_data_after_credit_note = [[100,100,30,100,-30]]

		self.assertEqual(expected_data_after_credit_note[0], report[1][0][7:12])


def make_sales_invoice():
	frappe.set_user("Administrator")

	si = create_sales_invoice(company="_Test Company 2",
			customer = '_Test Customer 2',
			currency = 'EUR',
			warehouse = 'Finished Goods - _TC2',
			debit_to = 'Debtors - _TC2',
			income_account = 'Sales - _TC2',
			expense_account = 'Cost of Goods Sold - _TC2',
			cost_center = '_Test Company 2 - _TC2',
			do_not_save=1)

	si.append('payment_schedule', dict(due_date=getdate(add_days(today(), 30)), invoice_portion=30.00, payment_amount=30))
	si.append('payment_schedule', dict(due_date=getdate(add_days(today(), 60)), invoice_portion=50.00, payment_amount=50))
	si.append('payment_schedule', dict(due_date=getdate(add_days(today(), 90)), invoice_portion=20.00, payment_amount=20))

	si.submit()

	return si.name

def make_payment(docname):
	pe = get_payment_entry("Sales Invoice", docname, bank_account="Cash - _TC2", party_amount=30)
	pe.paid_from = "Debtors - _TC2"
	pe.insert()
	pe.submit()


def make_credit_note(docname):
	create_sales_invoice(company="_Test Company 2",
			customer = '_Test Customer 2',
			currency = 'EUR',
			qty = -1,
			warehouse = 'Finished Goods - _TC2',
			debit_to = 'Debtors - _TC2',
			income_account = 'Sales - _TC2',
			expense_account = 'Cost of Goods Sold - _TC2',
			cost_center = '_Test Company 2 - _TC2',
			is_return = 1,
			return_against = docname)

