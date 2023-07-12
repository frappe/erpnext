# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, msgprint
from frappe.model.meta import get_field_precision
from frappe.utils import flt

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)

from erpnext.accounts.report.utils import (
	get_journal_entries,
	get_party_details,
	get_payment_entries,
	get_taxes_query,
)

from erpnext.accounts.report.utils import get_query_columns, get_values_for_columns


def execute(filters=None):
	return _execute(filters)


def _execute(filters, additional_table_columns=None):
	if not filters:
		filters = frappe._dict({})

	include_payments = filters.get("include_payments")
	invoice_list = get_invoices(filters, get_query_columns(additional_table_columns))
	if filters.get("include_payments"):
		if not filters.get("customer"):
			frappe.throw(_("Please select a customer for fetching payments."))
		invoice_list += get_payments(filters, additional_query_columns)

	columns, income_accounts, tax_accounts, unrealized_profit_loss_accounts = get_columns(
		invoice_list, additional_table_columns, include_payments
	)

	if not invoice_list:
		msgprint(_("No record found"))
		return columns, invoice_list

	invoice_income_map = get_invoice_income_map(invoice_list)
	internal_invoice_map = get_internal_invoice_map(invoice_list)
	invoice_income_map, invoice_tax_map = get_invoice_tax_map(
		invoice_list, invoice_income_map, income_accounts, include_payments
	)
	# Cost Center & Warehouse Map
	invoice_cc_wh_map = get_invoice_cc_wh_map(invoice_list)
	invoice_so_dn_map = get_invoice_so_dn_map(invoice_list)
	company_currency = frappe.get_cached_value("Company", filters.get("company"), "default_currency")
	mode_of_payments = get_mode_of_payments([inv.name for inv in invoice_list])
	customers = list(set(d.customer for d in invoice_list))
	customer_details = get_party_details("Customer", customers)

	data = []
	for inv in invoice_list:
		# invoice details
		sales_order = list(set(invoice_so_dn_map.get(inv.name, {}).get("sales_order", [])))
		delivery_note = list(set(invoice_so_dn_map.get(inv.name, {}).get("delivery_note", [])))
		cost_center = list(set(invoice_cc_wh_map.get(inv.name, {}).get("cost_center", [])))
		warehouse = list(set(invoice_cc_wh_map.get(inv.name, {}).get("warehouse", [])))

		row = {
			"voucher_type": inv.doctype,
			"invoice": inv.name,
			"posting_date": inv.posting_date,
			"customer": inv.customer,
			"customer_name": inv.customer_name,
			**get_values_for_columns(additional_table_columns, inv),
			"customer_group": customer_details.get(inv.customer).get("customer_group"),
			"territory": customer_details.get(inv.customer).get("territory"),
			"tax_id": customer_details.get(inv.customer).get("tax_id"),
			"receivable_account": inv.debit_to,
			"mode_of_payment": ", ".join(mode_of_payments.get(inv.name, [])),
			"project": inv.project,
			"owner": inv.owner,
			"remarks": inv.remarks,
			"sales_order": ", ".join(sales_order),
			"delivery_note": ", ".join(delivery_note),
			"cost_center": ", ".join(cost_center),
			"warehouse": ", ".join(warehouse),
			"currency": company_currency,
		}

		# map income values
		base_net_total = 0
		for income_acc in income_accounts:
			if inv.is_internal_customer and inv.company == inv.represents_company:
				income_amount = 0
			else:
				income_amount = flt(invoice_income_map.get(inv.name, {}).get(income_acc))

			base_net_total += income_amount
			row.update({frappe.scrub(income_acc): income_amount})

		# Add amount in unrealized account
		for account in unrealized_profit_loss_accounts:
			row.update(
				{frappe.scrub(account + "_unrealized"): flt(internal_invoice_map.get((inv.name, account)))}
			)

		# net total
		row.update({"net_total": base_net_total or inv.base_net_total})

		# tax account
		total_tax = 0
		for tax_acc in tax_accounts:
			if tax_acc not in income_accounts:
				tax_amount_precision = (
					get_field_precision(
						frappe.get_meta("Sales Taxes and Charges").get_field("tax_amount"), currency=company_currency
					)
					or 2
				)
				tax_amount = flt(invoice_tax_map.get(inv.name, {}).get(tax_acc), tax_amount_precision)
				total_tax += tax_amount
				row.update({frappe.scrub(tax_acc): tax_amount})

		# total tax, grand total, outstanding amount & rounded total

		row.update(
			{
				"tax_total": total_tax,
				"grand_total": inv.base_grand_total,
				"rounded_total": inv.base_rounded_total,
				"outstanding_amount": inv.outstanding_amount,
			}
		)

		data.append(row)

	return columns, sorted(data, key=lambda x: x["posting_date"])


def get_columns(invoice_list, additional_table_columns, include_payments=False):
	"""return columns based on filters"""
	columns = [
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"width": 120,
		},
		{
			"label": _("Voucher"),
			"fieldname": "invoice",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 120,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 80},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 120,
		},
		{"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 120},
	]

	if additional_table_columns:
		columns += additional_table_columns

	columns += [
		{
			"label": _("Customer Group"),
			"fieldname": "customer_group",
			"fieldtype": "Link",
			"options": "Customer Group",
			"width": 120,
		},
		{
			"label": _("Territory"),
			"fieldname": "territory",
			"fieldtype": "Link",
			"options": "Territory",
			"width": 80,
		},
		{"label": _("Tax Id"), "fieldname": "tax_id", "fieldtype": "Data", "width": 80},
		{
			"label": _("Receivable Account"),
			"fieldname": "receivable_account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 100,
		},
		{
			"label": _("Mode Of Payment"),
			"fieldname": "mode_of_payment",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 80,
		},
		{"label": _("Owner"), "fieldname": "owner", "fieldtype": "Data", "width": 100},
		{"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 150},
		{
			"label": _("Sales Order"),
			"fieldname": "sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 100,
		},
		{
			"label": _("Delivery Note"),
			"fieldname": "delivery_note",
			"fieldtype": "Link",
			"options": "Delivery Note",
			"width": 100,
		},
		{
			"label": _("Cost Center"),
			"fieldname": "cost_center",
			"fieldtype": "Link",
			"options": "Cost Center",
			"width": 100,
		},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 100,
		},
		{"fieldname": "currency", "label": _("Currency"), "fieldtype": "Data", "width": 80},
	]

	income_accounts = []
	tax_accounts = []
	income_columns = []
	tax_columns = []
	unrealized_profit_loss_accounts = []
	unrealized_profit_loss_account_columns = []

	if invoice_list:
		income_accounts = frappe.db.sql_list(
			"""select distinct income_account
			from `tabSales Invoice Item` where docstatus = 1 and parent in (%s)
			order by income_account"""
			% ", ".join(["%s"] * len(invoice_list)),
			tuple(inv.name for inv in invoice_list),
		)

		sales_taxes_query = get_taxes_query(invoice_list, "Sales Taxes and Charges", "Sales Invoice")
		sales_tax_accounts = sales_taxes_query.run(as_dict=True, pluck="account_head")
		tax_accounts = sales_tax_accounts

		if include_payments:
			advance_taxes_query = get_taxes_query(
				invoice_list, "Advance Taxes and Charges", "Payment Entry"
			)
			advance_tax_accounts = advance_taxes_query.run(as_dict=True, pluck="account_head")
			tax_accounts = set(tax_accounts + advance_tax_accounts)

		unrealized_profit_loss_accounts = frappe.db.sql_list(
			"""SELECT distinct unrealized_profit_loss_account
			from `tabSales Invoice` where docstatus = 1 and name in (%s)
			and is_internal_customer = 1
			and ifnull(unrealized_profit_loss_account, '') != ''
			order by unrealized_profit_loss_account"""
			% ", ".join(["%s"] * len(invoice_list)),
			tuple(inv.name for inv in invoice_list),
		)

	for account in income_accounts:
		income_columns.append(
			{
				"label": account,
				"fieldname": frappe.scrub(account),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			}
		)

	for account in tax_accounts:
		if account not in income_accounts:
			tax_columns.append(
				{
					"label": account,
					"fieldname": frappe.scrub(account),
					"fieldtype": "Currency",
					"options": "currency",
					"width": 120,
				}
			)

	for account in unrealized_profit_loss_accounts:
		unrealized_profit_loss_account_columns.append(
			{
				"label": account,
				"fieldname": frappe.scrub(account + "_unrealized"),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			}
		)

	net_total_column = [
		{
			"label": _("Net Total"),
			"fieldname": "net_total",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		}
	]

	total_columns = [
		{
			"label": _("Tax Total"),
			"fieldname": "tax_total",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Grand Total"),
			"fieldname": "grand_total",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Rounded Total"),
			"fieldname": "rounded_total",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Outstanding Amount"),
			"fieldname": "outstanding_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
	]

	columns = (
		columns
		+ income_columns
		+ unrealized_profit_loss_account_columns
		+ net_total_column
		+ tax_columns
		+ total_columns
	)

	return columns, income_accounts, tax_accounts, unrealized_profit_loss_accounts


def get_conditions(filters, payments=False):
	conditions = ""

	accounting_dimensions = get_accounting_dimensions(as_list=False) or []
	accounting_dimensions_list = [d.fieldname for d in accounting_dimensions]

	if filters.get("company"):
		conditions += " and company=%(company)s"

	if filters.get("customer") and "customer" not in accounting_dimensions_list:
		conditions += " and party = %(customer)s" if payments else " and customer = %(customer)s"

	if filters.get("from_date"):
		conditions += " and posting_date >= %(from_date)s"
	if filters.get("to_date"):
		conditions += " and posting_date <= %(to_date)s"

	if filters.get("owner"):
		conditions += " and owner = %(owner)s"

	def get_sales_invoice_item_field_condition(field, table="Sales Invoice Item") -> str:
		if not filters.get(field) or field in accounting_dimensions_list:
			return ""
		return f""" and exists(select name from `tab{table}`
				where parent=`tabSales Invoice`.name
					and ifnull(`tab{table}`.{field}, '') = %({field})s)"""

	conditions += get_sales_invoice_item_field_condition("mode_of_payment", "Sales Invoice Payment")
	conditions += get_sales_invoice_item_field_condition("cost_center")
	conditions += get_sales_invoice_item_field_condition("warehouse")
	conditions += get_sales_invoice_item_field_condition("brand")
	conditions += get_sales_invoice_item_field_condition("item_group")

	if accounting_dimensions:
		common_condition = """
			and exists(select name from `tabSales Invoice Item`
				where parent=`tabSales Invoice`.name
			"""
		for dimension in accounting_dimensions:
			if filters.get(dimension.fieldname):
				if frappe.get_cached_value("DocType", dimension.document_type, "is_tree"):
					filters[dimension.fieldname] = get_dimension_with_children(
						dimension.document_type, filters.get(dimension.fieldname)
					)

					conditions += (
						common_condition
						+ "and ifnull(`tabSales Invoice`.{0}, '') in %({0})s)".format(dimension.fieldname)
					)
				else:
					conditions += (
						common_condition
						+ "and ifnull(`tabSales Invoice`.{0}, '') in %({0})s)".format(dimension.fieldname)
					)

	return conditions


def get_invoices(filters, additional_query_columns):
	conditions = get_conditions(filters)
	return frappe.db.sql(
		"""
		select 'Sales Invoice' as doctype, name, posting_date, debit_to, project, customer,
		customer_name, owner, remarks, territory, tax_id, customer_group,
		base_net_total, base_grand_total, base_rounded_total, outstanding_amount,
		is_internal_customer, represents_company, company {0}
		from `tabSales Invoice`
		where docstatus = 1 {1}
		order by posting_date desc, name desc""".format(
			additional_query_columns, conditions
		),
		filters,
		as_dict=1,
	)


def get_payments(filters, additional_query_columns):
	if additional_query_columns:
		additional_query_columns = ", " + ", ".join(additional_query_columns)

	conditions = get_conditions(filters, payments=True)
	args = frappe._dict(
		account="debit_to",
		party="customer",
		party_name="customer_name",
		additional_query_columns="" if not additional_query_columns else additional_query_columns,
		conditions=conditions,
	)
	payment_entries = get_payment_entries(filters, args)
	journal_entries = get_journal_entries(filters, args)
	return payment_entries + journal_entries


def get_invoice_income_map(invoice_list):
	income_details = frappe.db.sql(
		"""select parent, income_account, sum(base_net_amount) as amount
		from `tabSales Invoice Item` where parent in (%s) group by parent, income_account"""
		% ", ".join(["%s"] * len(invoice_list)),
		tuple(inv.name for inv in invoice_list),
		as_dict=1,
	)

	invoice_income_map = {}
	for d in income_details:
		invoice_income_map.setdefault(d.parent, frappe._dict()).setdefault(d.income_account, [])
		invoice_income_map[d.parent][d.income_account] = flt(d.amount)

	return invoice_income_map


def get_internal_invoice_map(invoice_list):
	unrealized_amount_details = frappe.db.sql(
		"""SELECT name, unrealized_profit_loss_account,
		base_net_total as amount from `tabSales Invoice` where name in (%s)
		and is_internal_customer = 1 and company = represents_company"""
		% ", ".join(["%s"] * len(invoice_list)),
		tuple(inv.name for inv in invoice_list),
		as_dict=1,
	)

	internal_invoice_map = {}
	for d in unrealized_amount_details:
		if d.unrealized_profit_loss_account:
			internal_invoice_map.setdefault((d.name, d.unrealized_profit_loss_account), d.amount)

	return internal_invoice_map


def get_invoice_tax_map(invoice_list, invoice_income_map, income_accounts, include_payments=False):
	tax_details = frappe.db.sql(
		"""select parent, account_head,
		sum(base_tax_amount_after_discount_amount) as tax_amount
		from `tabSales Taxes and Charges` where parent in (%s) group by parent, account_head"""
		% ", ".join(["%s"] * len(invoice_list)),
		tuple(inv.name for inv in invoice_list),
		as_dict=1,
	)

	if include_payments:
		advance_tax_details = frappe.db.sql(
			"""
			select parent, account_head, case add_deduct_tax when "Add" then sum(base_tax_amount)
			else sum(base_tax_amount) * -1 end as tax_amount
			from `tabAdvance Taxes and Charges`
			where parent in (%s) and charge_type in ('On Paid Amount', 'Actual')
				and base_tax_amount != 0
			group by parent, account_head, add_deduct_tax
		"""
			% ", ".join(["%s"] * len(invoice_list)),
			tuple(inv.name for inv in invoice_list),
			as_dict=1,
		)
		tax_details += advance_tax_details

	invoice_tax_map = {}
	for d in tax_details:
		if d.account_head in income_accounts:
			if d.account_head in invoice_income_map[d.parent]:
				invoice_income_map[d.parent][d.account_head] += flt(d.tax_amount)
			else:
				invoice_income_map[d.parent][d.account_head] = flt(d.tax_amount)
		else:
			invoice_tax_map.setdefault(d.parent, frappe._dict()).setdefault(d.account_head, [])
			invoice_tax_map[d.parent][d.account_head] = flt(d.tax_amount)

	return invoice_income_map, invoice_tax_map


def get_invoice_so_dn_map(invoice_list):
	si_items = frappe.db.sql(
		"""select parent, sales_order, delivery_note, so_detail
		from `tabSales Invoice Item` where parent in (%s)
		and (ifnull(sales_order, '') != '' or ifnull(delivery_note, '') != '')"""
		% ", ".join(["%s"] * len(invoice_list)),
		tuple(inv.name for inv in invoice_list),
		as_dict=1,
	)

	invoice_so_dn_map = {}
	for d in si_items:
		if d.sales_order:
			invoice_so_dn_map.setdefault(d.parent, frappe._dict()).setdefault("sales_order", []).append(
				d.sales_order
			)

		delivery_note_list = None
		if d.delivery_note:
			delivery_note_list = [d.delivery_note]
		elif d.sales_order:
			delivery_note_list = frappe.db.sql_list(
				"""select distinct parent from `tabDelivery Note Item`
				where docstatus=1 and so_detail=%s""",
				d.so_detail,
			)

		if delivery_note_list:
			invoice_so_dn_map.setdefault(d.parent, frappe._dict()).setdefault(
				"delivery_note", delivery_note_list
			)

	return invoice_so_dn_map


def get_invoice_cc_wh_map(invoice_list):
	si_items = frappe.db.sql(
		"""select parent, cost_center, warehouse
		from `tabSales Invoice Item` where parent in (%s)
		and (ifnull(cost_center, '') != '' or ifnull(warehouse, '') != '')"""
		% ", ".join(["%s"] * len(invoice_list)),
		tuple(inv.name for inv in invoice_list),
		as_dict=1,
	)

	invoice_cc_wh_map = {}
	for d in si_items:
		if d.cost_center:
			invoice_cc_wh_map.setdefault(d.parent, frappe._dict()).setdefault("cost_center", []).append(
				d.cost_center
			)

		if d.warehouse:
			invoice_cc_wh_map.setdefault(d.parent, frappe._dict()).setdefault("warehouse", []).append(
				d.warehouse
			)

	return invoice_cc_wh_map


def get_mode_of_payments(invoice_list):
	mode_of_payments = {}
	if invoice_list:
		inv_mop = frappe.db.sql(
			"""select parent, mode_of_payment
			from `tabSales Invoice Payment` where parent in (%s) group by parent, mode_of_payment"""
			% ", ".join(["%s"] * len(invoice_list)),
			tuple(invoice_list),
			as_dict=1,
		)

		for d in inv_mop:
			mode_of_payments.setdefault(d.parent, []).append(d.mode_of_payment)

	return mode_of_payments
