# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, nowdate, flt, cstr
from frappe import msgprint, _
from erpnext.accounts.report.accounts_receivable.accounts_receivable import get_ageing_data

def execute(filters=None):
	if not filters: filters = {}
	supplier_naming_by = frappe.db.get_value("Buying Settings", None, "supp_master_name")
	columns = get_columns(supplier_naming_by)
	entries = get_gl_entries(filters)
	account_map = dict(((r.name, r) for r in frappe.db.sql("""select acc.name, 
		supp.supplier_name, supp.name as supplier 
		from `tabAccount` acc, `tabSupplier` supp 
		where acc.master_type="Supplier" and supp.name=acc.master_name""", as_dict=1)))

	entries_after_report_date = [[gle.voucher_type, gle.voucher_no] 
		for gle in get_gl_entries(filters, before_report_date=False)]

	account_supplier_type_map = get_account_supplier_type_map()
	voucher_detail_map = get_voucher_details()

	# Age of the invoice on this date
	age_on = getdate(filters.get("report_date")) > getdate(nowdate()) \
		and nowdate() or filters.get("report_date")

	data = []
	for gle in entries:
		if cstr(gle.against_voucher) == gle.voucher_no or not gle.against_voucher \
				or [gle.against_voucher_type, gle.against_voucher] in entries_after_report_date \
				or (gle.against_voucher_type == "Purchase Order"):
			voucher_details = voucher_detail_map.get(gle.voucher_type, {}).get(gle.voucher_no, {})
			
			invoiced_amount = gle.credit > 0 and gle.credit or 0
			outstanding_amount = get_outstanding_amount(gle, 
				filters.get("report_date") or nowdate())

			if abs(flt(outstanding_amount)) > 0.01:
				paid_amount = invoiced_amount - outstanding_amount
				row = [gle.posting_date, gle.account, gle.voucher_type, gle.voucher_no, 
					voucher_details.get("due_date", ""), voucher_details.get("bill_no", ""), 
					voucher_details.get("bill_date", ""), invoiced_amount, 
					paid_amount, outstanding_amount]
				
				# Ageing
				if filters.get("ageing_based_on") == "Due Date":
					ageing_based_on_date = voucher_details.get("due_date", "")
				else:
					ageing_based_on_date = gle.posting_date
					
				row += get_ageing_data(age_on, ageing_based_on_date, outstanding_amount) + \
					[account_map.get(gle.account, {}).get("supplier") or ""]

				if supplier_naming_by == "Naming Series":
					row += [account_map.get(gle.account, {}).get("supplier_name") or ""]

				row += [account_supplier_type_map.get(gle.account), gle.remarks]
				data.append(row)

	for i in range(0, len(data)):
		data[i].insert(4, """<a href="%s"><i class="icon icon-share" style="cursor: pointer;"></i></a>""" \
			% ("/".join(["#Form", data[i][2], data[i][3]]),))

	return columns, data
	
def get_columns(supplier_naming_by):
	columns = [
		_("Posting Date") + ":Date:80", _("Account") + ":Link/Account:150", _("Voucher Type") + "::110", 
		_("Voucher No") + "::120", "::30", _("Due Date") + ":Date:80", _("Bill No") + "::80", _("Bill Date") + ":Date:80", 
		_("Invoiced Amount") + ":Currency:100", _("Paid Amount") + ":Currency:100", 
		_("Outstanding Amount") + ":Currency:100", _("Age") + ":Int:50", "0-30:Currency:100", 
		"30-60:Currency:100", "60-90:Currency:100", _("90-Above") + ":Currency:100",
		_("Supplier") + ":Link/Supplier:150"
	]

	if supplier_naming_by == "Naming Series":
		columns += ["Supplier Name::110"]

	columns += ["Supplier Type:Link/Supplier Type:120", "Remarks::150"]

	return columns

def get_gl_entries(filters, before_report_date=True):
	conditions, supplier_accounts = get_conditions(filters, before_report_date)
	gl_entries = []
	gl_entries = frappe.db.sql("""select * from `tabGL Entry` 
		where docstatus < 2 %s order by posting_date, account""" % 
		(conditions), tuple(supplier_accounts), as_dict=1)
	return gl_entries
	
def get_conditions(filters, before_report_date=True):
	conditions = ""
	if filters.get("company"):
		conditions += " and company='%s'" % filters["company"].replace("'", "\'")
	
	supplier_accounts = []
	if filters.get("account"):
		supplier_accounts = [filters["account"]]
	else:
		supplier_accounts = frappe.db.sql_list("""select name from `tabAccount` 
			where ifnull(master_type, '') = 'Supplier' and docstatus < 2 %s""" % 
			conditions, filters)
	
	if supplier_accounts:
		conditions += " and account in (%s)" % (", ".join(['%s']*len(supplier_accounts)))
	else:
		msgprint(_("No Supplier Accounts found. Supplier Accounts are identified based on 'Master Type' value in account record."), raise_exception=1)
		
	if filters.get("report_date"):
		if before_report_date:
			conditions += " and posting_date<='%s'" % filters["report_date"]
		else:
			conditions += " and posting_date>'%s'" % filters["report_date"]
		
	return conditions, supplier_accounts
	
def get_account_supplier_type_map():
	account_supplier_type_map = {}
	for each in frappe.db.sql("""select acc.name, supp.supplier_type from `tabSupplier` supp, 
			`tabAccount` acc where supp.name = acc.master_name group by acc.name"""):
		account_supplier_type_map[each[0]] = each[1]

	return account_supplier_type_map
	
def get_voucher_details():
	voucher_details = {}
	for dt in ["Purchase Invoice", "Journal Voucher"]:
		voucher_details.setdefault(dt, frappe._dict())
		for t in frappe.db.sql("""select name, due_date, bill_no, bill_date 
				from `tab%s`""" % dt, as_dict=1):
			voucher_details[dt].setdefault(t.name, t)
		
	return voucher_details

def get_outstanding_amount(gle, report_date):
	payment_amount = frappe.db.sql("""
		select sum(ifnull(debit, 0)) - sum(ifnull(credit, 0)) 
		from `tabGL Entry` 
		where account = %s and posting_date <= %s and against_voucher_type = %s 
		and against_voucher = %s and name != %s""", 
		(gle.account, report_date, gle.voucher_type, gle.voucher_no, gle.name))[0][0]
		
	outstanding_amount = flt(gle.credit) - flt(gle.debit) - flt(payment_amount)
	return outstanding_amount
