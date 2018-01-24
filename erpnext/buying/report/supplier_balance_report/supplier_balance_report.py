# encoding: utf-8
# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate, getdate, flt, add_days
from datetime import datetime
import datetime
from datetime import date
from dateutil.relativedelta import relativedelta


def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data
	
def get_columns(filters):
	return [
		_("Name") + ":Link/Supplier:240",
		_("Supplier Group") + "::150",
		_("Annual Billing") + "::120",
		_("Total Unpaid") + "::120",
		]


def get_conditions(filters):
	conditions = ""

	if filters.get("from_date"): conditions += " and creation>=%(from_date)s"
	if filters.get("to_date"): conditions += " and creation<=%(to_date)s"
	
	return conditions


def get_data(filters):
	conditions = get_conditions(filters)

	li_list=frappe.db.sql("select * from `tabSupplier` where docstatus = 0 %s order by creation " % conditions, filters,as_dict=1)
	
	data = []
	for supp in li_list:

		billing_this_year = frappe.db.sql("""
			select sum(credit_in_account_currency) - sum(debit_in_account_currency)
			from `tabGL Entry`
			where voucher_type='Purchase Invoice' and party_type = 'Supplier'
				and party=%s and fiscal_year = %s""",
			(supp.name, frappe.db.get_default("fiscal_year")))

		total_unpaid = frappe.db.sql("""select sum(outstanding_amount)
			from `tabPurchase Invoice`
			where supplier=%s and docstatus = 1""", supp.name)


		row = [
		supp.name,
		supp.supplier_type,
		billing_this_year[0][0] if billing_this_year else 0,
		total_unpaid[0][0] if total_unpaid else 0,
		]
		data.append(row)
	return data
