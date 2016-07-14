
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
import random
from frappe.utils import random_string
from frappe.desk import query_report

def work():
	frappe.set_user(frappe.db.get_global('demo_accounts_user'))

	if random.random() < 0.5:
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

	if random.random() < 0.5:
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

	from erpnext.accounts.doctype.journal_entry.journal_entry import get_payment_entry_against_invoice

	if random.random() < 0.5:
		report = "Accounts Receivable"
		for si in list(set([r[3] for r in query_report.run(report,
		{"report_date": frappe.flags.current_date })["result"]
		if r[2]=="Sales Invoice"]))[:random.randint(1, 5)]:
			jv = frappe.get_doc(get_payment_entry_against_invoice("Sales Invoice", si))
			jv.posting_date = frappe.flags.current_date
			jv.cheque_no = random_string(6)
			jv.cheque_date = frappe.flags.current_date
			jv.insert()
			jv.submit()
			frappe.db.commit()

	if random.random() < 0.5:
		report = "Accounts Payable"
		for pi in list(set([r[3] for r in query_report.run(report,
			{"report_date": frappe.flags.current_date })["result"]
				if r[2]=="Purchase Invoice"]))[:random.randint(1, 5)]:
			jv = frappe.get_doc(get_payment_entry_against_invoice("Purchase Invoice", pi))
			jv.posting_date = frappe.flags.current_date
			jv.cheque_no = random_string(6)
			jv.cheque_date = frappe.flags.current_date
			jv.insert()
			jv.submit()
			frappe.db.commit()
