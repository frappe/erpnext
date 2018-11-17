# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.accounts.report.accounts_receivable.accounts_receivable import get_ageing_data
from frappe.utils import getdate, flt

def execute(filters=None):
	if not filters: filters = {}
	validate_filters(filters)

	columns = get_columns(filters)
	entries = get_entries(filters)
	invoice_details = get_invoice_posting_date_map(filters)

	data = []
	for d in entries:
		invoice = invoice_details.get(d.against_voucher) or frappe._dict()
		
		if d.reference_type=="Purchase Invoice":
			payment_amount = flt(d.debit) or -1 * flt(d.credit)
		else:
			payment_amount = flt(d.credit) or -1 * flt(d.debit)
		if d.party_type == "Customer":
			datas = frappe.db.sql("""
					select customer_name,customer_group  from `tabCustomer` 
					where name = %s """,(d.party))
			for customer_data in datas:

				result_data = customer_data
				customer_result = result_data	
						
				party_name = customer_result[0]
				customer_group = customer_result[1]

			row = [d.voucher_type, d.voucher_no, d.party_type, d.party,party_name,customer_group, d.posting_date,   				d.against_voucher,invoice.posting_date, invoice.due_date, d.debit, d.credit, d.remarks]

			if d.against_voucher:
				row += get_ageing_data(30, 60, 90, d.posting_date, invoice.posting_date, payment_amount)
			else:
				row += ["", "", "", "", ""]
			if invoice.due_date:
				row.append((getdate(d.posting_date) - getdate(invoice.due_date)).days or 0)
			
			data.append(row)
		elif d.party_type == "Supplier":
				datas = frappe.db.sql("""
						select supplier_name,supplier_group  from `tabSupplier` 
						where name = %s """,(d.party))
				for supplier_data in datas:
					
					result_data = supplier_data
					supplier_result = result_data	
							
					party_name = supplier_result[0]
					supplier_group = supplier_result[1]


				row = [d.voucher_type, d.voucher_no, d.party_type, d.party,party_name,supplier_group, d.posting_date,   				d.against_voucher,invoice.posting_date, invoice.due_date, d.debit, d.credit, d.remarks]

				if d.against_voucher:
					row += get_ageing_data(30, 60, 90, d.posting_date, invoice.posting_date, payment_amount)
				else:
					row += ["", "", "", "", ""]
				if invoice.due_date:
					row.append((getdate(d.posting_date) - getdate(invoice.due_date)).days or 0)
				
				data.append(row)

	return columns, data

		
def validate_filters(filters):
	if (filters.get("payment_type") == "Incoming" and filters.get("party_type") == "Supplier") or \
		(filters.get("payment_type") == "Outgoing" and filters.get("party_type") == "Customer"):
			frappe.throw(_("{0} payment entries can not be filtered by {1}")\
				.format(filters.payment_type, filters.party_type))

def get_columns(filters):
	return [
		_("Payment Document") + ":: 100",
		_("Payment Entry") + ":Dynamic Link/"+_("Payment Document")+":140",
		_("Party Type") + "::100", 
		_("Party") + ":Dynamic Link/Party Type:140",
		_("Party Name") + "::150",
		_("Party Group") + "::150",
		_("Posting Date") + ":Date:100",
		_("Invoice") + (":Link/Purchase Invoice:130" if filters.get("payment_type") == "Outgoing" else ":Link/Sales Invoice:130"),
		_("Invoice Posting Date") + ":Date:130", 
		_("Payment Due Date") + ":Date:130", 
		_("Debit") + ":Currency:120", 
		_("Credit") + ":Currency:120",
		_("Remarks") + "::150", 
		_("Age") +":Int:40",
		"0-30:Currency:100", 
		"30-60:Currency:100", 
		"60-90:Currency:100", 
		_("90-Above") + ":Currency:100",
		_("Delay in payment (Days)") + "::150"
	]

def get_conditions(filters):
	conditions = []

	if not filters.party_type:
		if filters.payment_type == "Outgoing":
			filters.party_type = "Supplier"
		else:
			filters.party_type = "Customer"

	if filters.party_type:
		conditions.append("party_type=%(party_type)s")

	if filters.party:
		conditions.append("party=%(party)s")
		
	if filters.party_type:
		conditions.append("against_voucher_type=%(reference_type)s")
		filters["reference_type"] = "Sales Invoice" if filters.party_type=="Customer" else "Purchase Invoice"

	if filters.get("from_date"):
		conditions.append("posting_date >= %(from_date)s")
		
	if filters.get("to_date"):
		conditions.append("posting_date <= %(to_date)s")

	return "and " + " and ".join(conditions) if conditions else ""

def get_entries(filters):
	return frappe.db.sql("""select 
		voucher_type, voucher_no, party_type, party,party_name, posting_date, debit, credit, remarks, against_voucher
		from `tabGL Entry`
		where company=%(company)s and voucher_type in ('Journal Entry', 'Payment Entry') {0}
	""".format(get_conditions(filters)), filters, as_dict=1)

def get_invoice_posting_date_map(filters):
	invoice_details = {}
	dt = "Sales Invoice" if filters.get("payment_type") == "Incoming" else "Purchase Invoice"
	for t in frappe.db.sql("select name, posting_date, due_date from `tab{0}`".format(dt), as_dict=1):
		invoice_details[t.name] = t

	return invoice_details
