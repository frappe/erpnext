
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
import random
from frappe.utils import random_string
from frappe.desk import query_report
from erpnext.accounts.doctype.journal_entry.journal_entry import get_payment_entry_against_invoice
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

def work():
	frappe.set_user(frappe.db.get_global('demo_accounts_user'))

	if random.random() <= 0.6:
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
		report = "Ordered Items to be Billed"
		for so in list(set([r[0] for r in query_report.run(report)["result"]
				if r[0]!="Total"]))[:random.randint(1, 5)]:
			si = frappe.get_doc(make_sales_invoice(so))
			si.posting_date = frappe.flags.current_date
			for d in si.get("items"):
				if not d.income_account:
					d.income_account = "Sales - {}".format(frappe.db.get_value('Company', si.company, 'abbr'))
			si.insert()
			si.submit()
			frappe.db.commit()

	if random.random() <= 0.6:
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice
		report = "Received Items to be Billed"
		for pr in list(set([r[0] for r in query_report.run(report)["result"]
			if r[0]!="Total"]))[:random.randint(1, 5)]:
			pi = frappe.get_doc(make_purchase_invoice(pr))
			pi.posting_date = frappe.flags.current_date
			pi.bill_no = random_string(6)
			pi.insert()
			pi.submit()
			frappe.db.commit()

	if random.random() <= 0.5:
		make_payment_entries("Sales Invoice", "Accounts Receivable")

	if random.random() <= 0.5:
		make_payment_entries("Purchase Invoice", "Accounts Payable")

def make_payment_entries(ref_doctype, report):
	outstanding_invoices = list(set([r[3] for r in query_report.run(report, 
	{"report_date": frappe.flags.current_date })["result"] if r[2]==ref_doctype]))
	
	# make payment via JV
	for inv in outstanding_invoices[:random.randint(1, 2)]:
		jv = frappe.get_doc(get_payment_entry_against_invoice(ref_doctype, inv))
		jv.posting_date = frappe.flags.current_date
		jv.cheque_no = random_string(6)
		jv.cheque_date = frappe.flags.current_date
		jv.insert()
		jv.submit()
		frappe.db.commit()
		outstanding_invoices.remove(inv)
		
	# make Payment Entry
	for inv in outstanding_invoices[:random.randint(1, 3)]:
		pe = get_payment_entry(ref_doctype, inv)
		pe.posting_date = frappe.flags.current_date
		pe.reference_no = random_string(6)
		pe.reference_date = frappe.flags.current_date
		pe.insert()
		pe.submit()
		frappe.db.commit()