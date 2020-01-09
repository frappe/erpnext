# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.utils import flt
from frappe.model.meta import get_field_precision
from frappe.utils.xlsxutils import handle_html
from erpnext.accounts.report.sales_register.sales_register import get_mode_of_payments

def execute(filters=None):
	return _execute(filters)

def _execute(filters=None, additional_table_columns=None, additional_query_columns=None):
	if not filters: filters = {}
	filters.update({"from_date": filters.get("date_range") and filters.get("date_range")[0], "to_date": filters.get("date_range") and filters.get("date_range")[1]})
	columns = get_columns(additional_table_columns, filters)

	company_currency = frappe.get_cached_value('Company',  filters.get("company"),  "default_currency")

	item_list = get_items(filters, additional_query_columns)
	if item_list:
		itemised_tax, tax_columns = get_tax_accounts(item_list, columns, company_currency)

	columns.append({
		'fieldname': 'currency',
		'label': _('Currency'),
		'fieldtype': 'Currency',
		'width': 80,
		'hidden': 1
	})

	mode_of_payments = get_mode_of_payments(set([d.parent for d in item_list]))
	so_dn_map = get_delivery_notes_against_sales_order(item_list)

	if filters.get('group_by'):
		grand_total = get_grand_total(filters)

	data = []
	prev_group_by_value = ''

	for d in item_list:
		delivery_note = None
		if d.delivery_note:
			delivery_note = d.delivery_note
		elif d.so_detail:
			delivery_note = ", ".join(so_dn_map.get(d.so_detail, []))

		if not delivery_note and d.update_stock:
			delivery_note = d.parent


		if filters.get('group_by'):
			if filters.get('group_by') == 'Item':
				group_by_field = 'item_code'
			elif filters.get('group_by') == 'Invoice':
				group_by_field = 'parent'
			else:
				group_by_field = frappe.scrub(filters.get('group_by'))

			if prev_group_by_value != d.get(group_by_field):
				if prev_group_by_value:
					total_row['percent_gt'] = flt(total_row['total']/grand_total * 100)
					data.append(total_row)
					data.append({})

				prev_group_by_value = d.get(group_by_field)

				total_row = {
					'item_code': d.get(group_by_field),
					'stock_qty': 0.0,
					'amount': 0.0,
					'bold': 1,
					'total_tax': 0.0,
					'total': 0.0
				}

		row = {
			'item_code': d.item_code,
			'item_name': d.item_name,
			'item_group': d.item_group,
			'description': d.description,
			'invoice': d.parent,
			'posting_date': d.posting_date,
			'customer': d.customer,
			'customer_name': d.customer_name
		}

		if additional_query_columns:
			for col in additional_query_columns:
				row.update({
					col: d.get(col)
				})

		row.update({
			'customer_group': d.customer_group,
			'debit_to': d.debit_to,
			'mode_of_payment': ", ".join(mode_of_payments.get(d.parent, [])),
			'territory': d.territory,
			'project': d.project,
			'company': d.company,
			'sales_order': d.sales_order,
			'delivery_note': d.delivery_note,
			'income_account': d.income_account,
			'cost_center': d.cost_center,
			'stock_qty': d.stock_qty,
			'stock_uom': d.stock_uom
		})

		if d.stock_uom != d.uom and d.stock_qty:
			row.update({
				'rate': (d.base_net_rate * d.qty)/d.stock_qty,
				'amount': d.base_net_amount
			})
		else:
			row.update({
				'rate': d.base_net_rate,
				'amount': d.base_net_amount
			})

		total_tax = 0
		for tax in tax_columns:
			item_tax = itemised_tax.get(d.name, {}).get(tax, {})
			row.update({
				frappe.scrub(tax + ' Rate'): item_tax.get("tax_rate", 0),
				frappe.scrub(tax + ' Amount'): item_tax.get("tax_amount", 0),
			})
			total_tax += flt(item_tax.get("tax_amount"))

		row.update({
			'total_tax': total_tax,
			'total': d.base_net_amount + total_tax,
			'currency': company_currency
		})

		if filters.get('group_by'):
			total_row['stock_qty'] += row['stock_qty']
			total_row['amount'] += row['amount']
			total_row['total_tax'] += row['total_tax']
			total_row['total'] += row['total']

		data.append(row)

	if filters.get('group_by'):
		total_row['percent_gt'] = frappe.bold(total_row['total']/grand_total * 100)
		data.append(total_row)
		data.append({})

	return columns, data

def get_columns(additional_table_columns, filters):
	columns = [
		{
			'label': _('Item Code'),
			'fieldname': 'item_code',
			'fieldtype': 'Link',
			'options': 'Item',
			'width': 120
		},
		{
			'label': _('Item Name'),
			'fieldname': 'item_name',
			'fieldtype': 'Data',
			'width': 120
		},
		{
			'label': _('Item Group'),
			'fieldname': 'item_group',
			'fieldtype': 'Link',
			'options': 'Item Group',
			'width': 120
		},
		{
			'label': _('Description'),
			'fieldname': 'description',
			'fieldtype': 'Data',
			'width': 150
		},
		{
			'label': _('Invoice'),
			'fieldname': 'invoice',
			'fieldtype': 'Link',
			'options': 'Sales Invoice',
			'width': 120
		},
		{
			'label': _('Posting Date'),
			'fieldname': 'posting_date',
			'fieldtype': 'Date',
			'width': 120
		},
		{
			'label': _('Customer'),
			'fieldname': 'customer',
			'fieldtype': 'Link',
			'options': 'Customer',
			'width': 120
		},
		{
			'label': _('Customer Name'),
			'fieldname': 'customer_name',
			'fieldtype': 'Data',
			'width': 120
		}
	]

	if additional_table_columns:
		columns += additional_table_columns

	columns += [
		{
			'label': _('Customer Group'),
			'fieldname': 'customer_group',
			'fieldtype': 'Link',
			'options': 'Customer Group',
			'width': 120
		},
		{
			'label': _('Receivable Account'),
			'fieldname': 'debit_to',
			'fieldtype': 'Link',
			'options': 'Account',
			'width': 80
		},
		{
			'label': _('Mode Of Payment'),
			'fieldname': 'mode_of_payment',
			'fieldtype': 'Data',
			'width': 120
		},
		{
			'label': _("Territory"),
			'fieldname': 'territory',
			'fieldtype': 'Link',
			'options': 'Territory',
			'width': 80
		},
		{
			'label': _('Project'),
			'fieldname': 'project',
			'fieldtype': 'Link',
			'options': 'Project',
			'width': 80
		},
		{
			'label': _('Company'),
			'fieldname': 'company',
			'fieldtype': 'Link',
			'options': 'Company',
			'width': 80
		},
		{
			'label': _('Sales Order'),
			'fieldname': 'sales_order',
			'fieldtype': 'Link',
			'options': 'Sales Order',
			'width': 100
		},
		{
			'label': _("Delivery Note"),
			'fieldname': 'delivery_note',
			'fieldtype': 'Link',
			'options': 'Delivery Note',
			'width': 100
		},
		{
			'label': _('Income Account'),
			'fieldname': 'income_account',
			'fieldtype': 'Link',
			'options': 'Account',
			'width': 100
		},
		{
			'label': _("Cost Center"),
			'fieldname': 'cost_center',
			'fieldtype': 'Link',
			'options': 'Cost Center',
			'width': 100
		},
		{
			'label': _('Stock Qty'),
			'fieldname': 'stock_qty',
			'fieldtype': 'Float',
			'width': 100
		},
		{
			'label': _('Stock UOM'),
			'fieldname': 'stock_uom',
			'fieldtype': 'Link',
			'options': 'UOM',
			'width': 100
		},
		{
			'label': _('Rate'),
			'fieldname': 'rate',
			'fieldtype': 'Float',
			'options': 'currency',
			'width': 100
		},
		{
			'label': _('Amount'),
			'fieldname': 'amount',
			'fieldtype': 'Currency',
			'options': 'currency',
			'width': 100
		}
	]

	if filters.get('group_by'):
		columns.append({
			'label': _('% Of Grand Total'),
			'fieldname': 'percent_gt',
			'fieldtype': 'Float',
			'width': 80
		})

	return columns

def get_conditions(filters):
	conditions = ""

	for opts in (("company", " and company=%(company)s"),
		("customer", " and `tabSales Invoice`.customer = %(customer)s"),
		("item_code", " and `tabSales Invoice Item`.item_code = %(item_code)s"),
		("from_date", " and `tabSales Invoice`.posting_date>=%(from_date)s"),
		("to_date", " and `tabSales Invoice`.posting_date<=%(to_date)s")):
			if filters.get(opts[0]):
				conditions += opts[1]

	if filters.get("mode_of_payment"):
		conditions += """ and exists(select name from `tabSales Invoice Payment`
			where parent=`tabSales Invoice`.name
				and ifnull(`tabSales Invoice Payment`.mode_of_payment, '') = %(mode_of_payment)s)"""

	if filters.get("warehouse"):
		conditions +=  """ and exists(select name from `tabSales Invoice Item`
			 where parent=`tabSales Invoice`.name
			 	and ifnull(`tabSales Invoice Item`.warehouse, '') = %(warehouse)s)"""


	if filters.get("brand"):
		conditions +=  """ and exists(select name from `tabSales Invoice Item`
			 where parent=`tabSales Invoice`.name
			 	and ifnull(`tabSales Invoice Item`.brand, '') = %(brand)s)"""

	if filters.get("item_group"):
		conditions +=  """ and exists(select name from `tabSales Invoice Item`
			 where parent=`tabSales Invoice`.name
			 	and ifnull(`tabSales Invoice Item`.item_group, '') = %(item_group)s)"""

	if not filters.get("group_by"):
		conditions += "ORDER BY `tabSales Invoice`.posting_date desc, `tabSales Invoice Item`.item_code desc"

	if filters.get("group_by"):
		if filters.get("group_by") == 'Invoice':
			conditions += " ORDER BY `tabSales Invoice Item`.parent desc"
		elif filters.get("group_by") == 'Item':
			conditions += " ORDER BY `tabSales Invoice Item`.item_code desc"
		else:
			conditions += " ORDER BY {0}".format(frappe.scrub(filters.get("group_by")))

	return conditions

def get_items(filters, additional_query_columns):
	conditions = get_conditions(filters)
	match_conditions = frappe.build_match_conditions("Sales Invoice")

	if match_conditions:
		match_conditions = " and {0} ".format(match_conditions)

	if additional_query_columns:
		additional_query_columns = ', ' + ', '.join(additional_query_columns)

	return frappe.db.sql("""
		select
			`tabSales Invoice Item`.name, `tabSales Invoice Item`.parent,
			`tabSales Invoice`.posting_date, `tabSales Invoice`.debit_to,
			`tabSales Invoice`.project, `tabSales Invoice`.customer, `tabSales Invoice`.remarks,
			`tabSales Invoice`.territory, `tabSales Invoice`.company, `tabSales Invoice`.base_net_total,
			`tabSales Invoice Item`.item_code, `tabSales Invoice Item`.item_name,
			`tabSales Invoice Item`.item_group, `tabSales Invoice Item`.description, `tabSales Invoice Item`.sales_order,
			`tabSales Invoice Item`.delivery_note, `tabSales Invoice Item`.income_account,
			`tabSales Invoice Item`.cost_center, `tabSales Invoice Item`.stock_qty,
			`tabSales Invoice Item`.stock_uom, `tabSales Invoice Item`.base_net_rate,
			`tabSales Invoice Item`.base_net_amount, `tabSales Invoice`.customer_name,
			`tabSales Invoice`.customer_group, `tabSales Invoice Item`.so_detail,
			`tabSales Invoice`.update_stock, `tabSales Invoice Item`.uom, `tabSales Invoice Item`.qty {0}
		from `tabSales Invoice`, `tabSales Invoice Item`
		where `tabSales Invoice`.name = `tabSales Invoice Item`.parent
			and `tabSales Invoice`.docstatus = 1 %s %s
		""".format(additional_query_columns or '') % (conditions, match_conditions), filters, as_dict=1)

def get_delivery_notes_against_sales_order(item_list):
	so_dn_map = frappe._dict()
	so_item_rows = list(set([d.so_detail for d in item_list]))

	if so_item_rows:
		delivery_notes = frappe.db.sql("""
			select parent, so_detail
			from `tabDelivery Note Item`
			where docstatus=1 and so_detail in (%s)
			group by so_detail, parent
		""" % (', '.join(['%s']*len(so_item_rows))), tuple(so_item_rows), as_dict=1)

		for dn in delivery_notes:
			so_dn_map.setdefault(dn.so_detail, []).append(dn.parent)

	return so_dn_map

def get_grand_total(filters):
	conditions = get_conditions(filters)

	return frappe.db.sql(""" SELECT
		SUM(`tabSales Invoice`.grand_total)
		FROM `tabSales Invoice`
		WHERE `tabSales Invoice`.docstatus = 1  %s
	""" % (conditions), filters)[0][0]

def get_deducted_taxes():
	return frappe.db.sql_list("select name from `tabPurchase Taxes and Charges` where add_deduct_tax = 'Deduct'")

def get_tax_accounts(item_list, columns, company_currency,
		doctype="Sales Invoice", tax_doctype="Sales Taxes and Charges"):
	import json
	item_row_map = {}
	tax_columns = []
	invoice_item_row = {}
	itemised_tax = {}

	tax_amount_precision = get_field_precision(frappe.get_meta(tax_doctype).get_field("tax_amount"),
		currency=company_currency) or 2

	for d in item_list:
		invoice_item_row.setdefault(d.parent, []).append(d)
		item_row_map.setdefault(d.parent, {}).setdefault(d.item_code or d.item_name, []).append(d)

	conditions = ""
	if doctype == "Purchase Invoice":
		conditions = " and category in ('Total', 'Valuation and Total') and base_tax_amount_after_discount_amount != 0"

	deducted_tax = get_deducted_taxes()
	tax_details = frappe.db.sql("""
		select
			name, parent, description, item_wise_tax_detail,
			charge_type, base_tax_amount_after_discount_amount
		from `tab%s`
		where
			parenttype = %s and docstatus = 1
			and (description is not null and description != '')
			and parent in (%s)
			%s
		order by description
	""" % (tax_doctype, '%s', ', '.join(['%s']*len(invoice_item_row)), conditions),
		tuple([doctype] + list(invoice_item_row)))

	for name, parent, description, item_wise_tax_detail, charge_type, tax_amount in tax_details:
		description = handle_html(description)
		if description not in tax_columns and tax_amount:
			# as description is text editor earlier and markup can break the column convention in reports
			tax_columns.append(description)

		if item_wise_tax_detail:
			try:
				item_wise_tax_detail = json.loads(item_wise_tax_detail)

				for item_code, tax_data in item_wise_tax_detail.items():
					itemised_tax.setdefault(item_code, frappe._dict())

					if isinstance(tax_data, list):
						tax_rate, tax_amount = tax_data
					else:
						tax_rate = tax_data
						tax_amount = 0

					if charge_type == "Actual" and not tax_rate:
						tax_rate = "NA"

					item_net_amount = sum([flt(d.base_net_amount)
						for d in item_row_map.get(parent, {}).get(item_code, [])])

					for d in item_row_map.get(parent, {}).get(item_code, []):
						item_tax_amount = flt((tax_amount * d.base_net_amount) / item_net_amount) \
							if item_net_amount else 0
						if item_tax_amount:
							tax_value = flt(item_tax_amount, tax_amount_precision)
							tax_value = (tax_value * -1
								if (doctype == 'Purchase Invoice' and name in deducted_tax) else tax_value)

							itemised_tax.setdefault(d.name, {})[description] = frappe._dict({
								"tax_rate": tax_rate,
								"tax_amount": tax_value
							})

			except ValueError:
				continue
		elif charge_type == "Actual" and tax_amount:
			for d in invoice_item_row.get(parent, []):
				itemised_tax.setdefault(d.name, {})[description] = frappe._dict({
					"tax_rate": "NA",
					"tax_amount": flt((tax_amount * d.base_net_amount) / d.base_net_total,
						tax_amount_precision)
				})

	tax_columns.sort()
	for desc in tax_columns:
		columns.append({
			'label': _(desc + ' Rate'),
			'fieldname': frappe.scrub(desc + ' Rate'),
			'fieldtype': 'Float',
			'width': 100
		})

		columns.append({
			'label': _(desc + ' Amount'),
			'fieldname': frappe.scrub(desc + ' Amount'),
			'fieldtype': 'Currency',
			'options': 'currency',
			'width': 100
		})

	columns += [
		{
			'label': _('Total Tax'),
			'fieldname': 'total_tax',
			'fieldtype': 'Currency',
			'options': 'currency',
			'width': 100
		},
		{
			'label': _('Total'),
			'fieldname': 'total',
			'fieldtype': 'Currency',
			'options': 'currency',
			'width': 100
		}
	]

	return itemised_tax, tax_columns
