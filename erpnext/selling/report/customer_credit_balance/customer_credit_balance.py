# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from erpnext.selling.doctype.customer.customer import get_credit_limit
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions

def execute(filters=None):
	if not filters: filters = {}
	#Check if customer id is according to naming series or customer name
	customer_naming_type = frappe.db.get_value("Selling Settings", None, "cust_master_name")
	columns = get_columns(customer_naming_type)

	data = []

	customer_list = get_details(filters)

	for d in customer_list:
		row = []

		outstanding_amt = get_customer_outstanding(filters, ignore_outstanding_sales_order=d.bypass_credit_limit_check_at_sales_order)

		credit_limit = get_credit_limit(d.name, filters.get("company"))

		bal = flt(credit_limit) - flt(outstanding_amt)

		if customer_naming_type == "Naming Series":
			row = [d.name, d.customer_name, credit_limit, outstanding_amt, bal,
				d.bypass_credit_limit_check_at_sales_order, d.is_frozen,
          d.disabled]
		else:
			row = [d.name, credit_limit, outstanding_amt, bal,
          d.bypass_credit_limit_check_at_sales_order, d.is_frozen, d.disabled]

		if credit_limit:
			data.append(row)

	return columns, data

def get_columns(customer_naming_type):
	columns = [
		_("Customer") + ":Link/Customer:120",
		_("Credit Limit") + ":Currency:120",
		_("Outstanding Amt") + ":Currency:100",
		_("Credit Balance") + ":Currency:120",
		_("Bypass credit check at Sales Order ") + ":Check:80",
		_("Is Frozen") + ":Check:80",
		_("Disabled") + ":Check:80",
	]

	if customer_naming_type == "Naming Series":
		columns.insert(1, _("Customer Name") + ":Data:120")

	return columns

def get_details(filters):
	conditions = ""

	if filters.get("customer"):
		conditions += " where name = %(customer)s"

	return frappe.db.sql("""select name, customer_name,
		bypass_credit_limit_check_at_sales_order, is_frozen, disabled from `tabCustomer` %s
	""" % conditions, filters, as_dict=1)

def get_customer_outstanding(filters, ignore_outstanding_sales_order=False):
	# Outstanding based on GL Entries

	cond = ""
	if filters.get('cost_center'):
		lft, rgt = frappe.get_cached_value("Cost Center",
			cost_center, ['lft', 'rgt'])

		cond += """ and cost_center in (select name from `tabCost Center` where
			lft >= {0} and rgt <= {1})""".format(lft, rgt)

	if filters.get('customer'):
		cond += "and party = %(customer)s"

	accounting_dimensions = get_accounting_dimensions()

	if accounting_dimensions:
		for dimension in accounting_dimensions:
			if filters.get(dimension):
				cond += """ and {0} = %({0})s """.format(dimension)

	outstanding_based_on_gle = frappe.db.sql("""
		select sum(debit) - sum(credit)
		from `tabGL Entry` where party_type = 'Customer'
		and company=%(company)s {0}""".format(cond), filters, debug=1)

	outstanding_based_on_gle = flt(outstanding_based_on_gle[0][0]) if outstanding_based_on_gle else 0

	# Outstanding based on Sales Order
	outstanding_based_on_so = 0.0

	# if credit limit check is bypassed at sales order level,
	# we should not consider outstanding Sales Orders, when customer credit balance report is run
	if not ignore_outstanding_sales_order:
		outstanding_based_on_so = frappe.db.sql("""
			select sum(base_grand_total*(100 - per_billed)/100)
			from `tabSales Order`
			where customer=%s and docstatus = 1 and company=%s
			and per_billed < 100 and status != 'Closed'""", (filters.get('customer'), filters.get('company')))

		outstanding_based_on_so = flt(outstanding_based_on_so[0][0]) if outstanding_based_on_so else 0.0

	# Outstanding based on Delivery Note, which are not created against Sales Order
	unmarked_delivery_note_items = frappe.db.sql("""select
			dn_item.name, dn_item.amount, dn.base_net_total, dn.base_grand_total
		from `tabDelivery Note` dn, `tabDelivery Note Item` dn_item
		where
			dn.name = dn_item.parent
			and dn.customer=%s and dn.company=%s
			and dn.docstatus = 1 and dn.status not in ('Closed', 'Stopped')
			and ifnull(dn_item.against_sales_order, '') = ''
			and ifnull(dn_item.against_sales_invoice, '') = ''
		""", (filters.get('customer'), filters.get('company')), as_dict=True)

	outstanding_based_on_dn = 0.0

	for dn_item in unmarked_delivery_note_items:
		si_amount = frappe.db.sql("""select sum(amount)
			from `tabSales Invoice Item`
			where dn_detail = %s and docstatus = 1""", dn_item.name)[0][0]

		if flt(dn_item.amount) > flt(si_amount) and dn_item.base_net_total:
			outstanding_based_on_dn += ((flt(dn_item.amount) - flt(si_amount)) \
				/ dn_item.base_net_total) * dn_item.base_grand_total

	return outstanding_based_on_gle + outstanding_based_on_so + outstanding_based_on_dn
