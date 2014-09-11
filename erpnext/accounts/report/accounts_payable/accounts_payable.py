# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, nowdate, flt, cstr
from erpnext.accounts.report.accounts_receivable.accounts_receivable import get_ageing_data

def execute(filters=None):
	if not filters: filters = {}
	supplier_naming_by = frappe.db.get_value("Buying Settings", None, "supp_master_name")
	columns = get_columns(supplier_naming_by)
	entries = get_gl_entries(filters)

	entries_after_report_date = [[gle.voucher_type, gle.voucher_no]
		for gle in get_gl_entries(filters, before_report_date=False)]

	supplier_details = get_supplier_details()
	voucher_detail_map = get_voucher_details()

	# Age of the invoice on this date
	age_on = getdate(filters.get("report_date")) > getdate(nowdate()) \
		and nowdate() or filters.get("report_date")

	data = []
	for gle in entries:
		if cstr(gle.against_voucher) == gle.voucher_no or not gle.against_voucher \
				or [gle.against_voucher_type, gle.against_voucher] in entries_after_report_date:
			voucher_details = voucher_detail_map.get(gle.voucher_type, {}).get(gle.voucher_no, {})

			invoiced_amount = gle.credit > 0 and gle.credit or 0
			outstanding_amount = get_outstanding_amount(gle,
				filters.get("report_date") or nowdate())

			if abs(flt(outstanding_amount)) > 0.01:
				paid_amount = invoiced_amount - outstanding_amount
				row = [gle.posting_date, gle.party]

				if supplier_naming_by == "Naming Series":
					row += [supplier_details.get(gle.party, {}).supplier_name or ""]

				row += [gle.voucher_type, gle.voucher_no, voucher_details.get("due_date", ""),
					voucher_details.get("bill_no", ""), voucher_details.get("bill_date", ""),
					invoiced_amount, paid_amount, outstanding_amount]

				# Ageing
				if filters.get("ageing_based_on") == "Due Date":
					ageing_based_on_date = voucher_details.get("due_date", "")
				else:
					ageing_based_on_date = gle.posting_date

				row += get_ageing_data(age_on, ageing_based_on_date, outstanding_amount) + \
					[supplier_details.get(gle.party).supplier_type, gle.remarks]

				data.append(row)

	# for i in range(0, len(data)):
	# 	data[i].insert(4, """<a href="%s"><i class="icon icon-share" style="cursor: pointer;"></i></a>""" \
	# 		% ("/".join(["#Form", data[i][2], data[i][3]]),))

	return columns, data

def get_columns(supplier_naming_by):
	columns = [_("Posting Date") + ":Date:80", _("Supplier") + ":Link/Supplier:150"]

	if supplier_naming_by == "Naming Series":
		columns += ["Supplier Name::110"]

	columns +=[_("Voucher Type") + "::110", _("Voucher No") + "::120", "::30",
		_("Due Date") + ":Date:80", _("Bill No") + "::80", _("Bill Date") + ":Date:80",
		_("Invoiced Amount") + ":Currency:100", _("Paid Amount") + ":Currency:100",
		_("Outstanding Amount") + ":Currency:100", _("Age") + ":Int:50", "0-30:Currency:100",
		"30-60:Currency:100", "60-90:Currency:100", _("90-Above") + ":Currency:100",
		_("Supplier Type") + ":Link/Supplier Type:150", _("Remarks") + "::150"
	]

	return columns

def get_gl_entries(filters, before_report_date=True):
	conditions = get_conditions(filters, before_report_date)
	gl_entries = []
	gl_entries = frappe.db.sql("""select * from `tabGL Entry`
		where docstatus < 2 and party_type='Supplier' %s
		order by posting_date, party""" % conditions, as_dict=1)
	return gl_entries

def get_conditions(filters, before_report_date=True):
	conditions = ""
	if filters.get("company"):
		conditions += " and company='%s'" % filters["company"].replace("'", "\'")

	if filters.get("supplier"):
		conditions += " and party='%s'" % filters["supplier"].replace("'", "\'")

	if filters.get("report_date"):
		if before_report_date:
			conditions += " and posting_date<='%s'" % filters["report_date"]
		else:
			conditions += " and posting_date>'%s'" % filters["report_date"]

	return conditions

def get_supplier_details():
	supplier_details = {}
	for d in frappe.db.sql("""select name, supplier_type, supplier_name from `tabSupplier`""", as_dict=1):
		supplier_details.setdefault(d.name, d)

	return supplier_details

def get_voucher_details():
	voucher_details = {}
	for dt in ["Purchase Invoice", "Journal Voucher"]:
		voucher_details.setdefault(dt, frappe._dict())
		for t in frappe.db.sql("""select name, due_date, bill_no, bill_date from `tab%s`""" % dt, as_dict=1):
			voucher_details[dt].setdefault(t.name, t)

	return voucher_details

def get_outstanding_amount(gle, report_date):
	payment_amount = frappe.db.sql("""
		select sum(ifnull(debit, 0)) - sum(ifnull(credit, 0))
		from `tabGL Entry`
		where party_type='Supplier' and party = %s and posting_date <= %s and against_voucher_type = %s
		and against_voucher = %s and name != %s""",
		(gle.party, report_date, gle.voucher_type, gle.voucher_no, gle.name))[0][0]

	outstanding_amount = flt(gle.credit) - flt(gle.debit) - flt(payment_amount)
	return outstanding_amount
