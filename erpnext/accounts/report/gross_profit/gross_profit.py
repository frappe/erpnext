# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub, unscrub
from frappe.utils import flt, cstr, getdate, nowdate, cint
from frappe.desk.query_report import group_report_data
from six import string_types
import json


def execute(filters=None):
	return GrossProfitGenerator(filters).run()


class GrossProfitGenerator(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(self.filters.from_date or nowdate())
		self.filters.to_date = getdate(self.filters.to_date or nowdate())

		self.show_item_name = frappe.defaults.get_global_default('item_naming_by') != "Item Name"

		self.data = []

	def run(self):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("From Date must be before To Date"))

		self.load_invoice_items()
		self.prepare_data()
		self.get_cogs()

		data = self.get_grouped_data()
		columns = self.get_columns()

		return columns, data

	def load_invoice_items(self):
		conditions = self.get_conditions()

		self.data = frappe.db.sql("""
			select
				si.name as parent, si_item.parenttype, si_item.name, si_item.idx,
				si.posting_date, si.posting_time,
				si.customer, si.customer_name, c.customer_group, c.territory,
				si_item.item_code, si_item.item_name, si_item.batch_no, si_item.uom,
				si_item.warehouse, i.item_group, i.brand,
				si.update_stock, si_item.dn_detail, si_item.delivery_note,
				si_item.qty, si_item.stock_qty, si_item.conversion_factor, si_item.alt_uom_size,
				si_item.base_net_amount,
				si.depreciation_type, si_item.depreciation_percentage,
				GROUP_CONCAT(DISTINCT sp.sales_person SEPARATOR ', ') as sales_person,
				sum(ifnull(sp.allocated_percentage, 100)) as allocated_percentage,
				si_item.si_detail, si_item.returned_qty, si_item.base_returned_amount
			from `tabSales Invoice` si
			inner join `tabSales Invoice Item` si_item on si_item.parent = si.name
			left join `tabCustomer` c on c.name = si.customer
			left join `tabItem` i on i.name = si_item.item_code
			left join `tabSales Team` sp on sp.parent = si.name and sp.parenttype = 'Sales Invoice'
			where
				si.docstatus = 1 and si.is_return = 0 and si.is_opening != 'Yes' {conditions}
			group by si.name, si_item.name
			order by si.posting_date desc, si.posting_time desc, si.name desc, si_item.idx asc
		""".format(conditions=conditions), self.filters, as_dict=1)

	def prepare_data(self):
		for d in self.data:
			if "Group by Item" in [self.filters.group_by_1, self.filters.group_by_2, self.filters.group_by_3]:
				d['doc_type'] = "Sales Invoice"
				d['reference'] = d.parent
			else:
				d['doc_type'] = "Item"
				d['reference'] = d.item_code

			d["disable_item_formatter"] = cint(self.show_item_name)

			if d.depreciation_type:
				d.split_percentage = 100 - d.depreciation_percentage if d.depreciation_type == "After Depreciation Amount"\
					else d.depreciation_percentage
			else:
				d.split_percentage = 100

	def get_cogs(self):
		update_item_valuation_rates(self.data)

		for item in self.data:
			item.cogs_per_unit = flt(item.valuation_rate) * flt(item.conversion_factor)
			item.cogs_per_unit = item.cogs_per_unit * item.split_percentage / 100

			item.cogs_qty = flt(item.qty) - flt(item.get('returned_qty'))
			item.cogs = item.cogs_per_unit * item.cogs_qty

			self.postprocess_row(item)
			item.gross_profit_per_unit = item.gross_profit / item.cogs_qty if item.cogs_qty else 0

	def get_grouped_data(self):
		data = self.data

		self.group_by = [None]
		for i in range(3):
			group_label = self.filters.get("group_by_" + str(i + 1), "").replace("Group by ", "")

			if not group_label or group_label == "Ungrouped":
				continue

			if group_label == "Invoice":
				group_field = "parent"
			elif group_label == "Item":
				group_field = "item_code"
			elif group_label == "Customer Group":
				group_field = "customer_group"
			else:
				group_field = scrub(group_label)

			self.group_by.append(group_field)

		if len(self.group_by) <= 1:
			return data

		def sort_group(group_object, group_by_map):
			group_object.per_gross_profit = group_object.totals.per_gross_profit
			group_object.rows = sorted(group_object.rows, key=lambda d: -flt(d.per_gross_profit))

		return group_report_data(data, self.group_by, calculate_totals=self.calculate_group_totals,
			postprocess_group=sort_group)

	def calculate_group_totals(self, data, group_field, group_value, grouped_by):
		total_fields = [
			'qty', 'stock_qty', 'cogs',
			'base_net_amount', 'returned_qty', 'base_returned_amount'
		]

		totals = frappe._dict()

		# Copy grouped by into total row
		for f, g in grouped_by.items():
			totals[f] = g

		# Set zeros
		for f in total_fields:
			totals[f] = 0

		# Add totals
		for d in data:
			for f in total_fields:
				totals[f] += flt(d[f])

		# Set group values
		if data:
			if 'parent' in grouped_by:
				totals['posting_date'] = data[0].get('posting_date')
				totals['customer'] = data[0].get('customer')
				totals['sales_person'] = data[0].get('sales_person')

			if 'item_code' in grouped_by:
				totals['item_name'] = data[0].get('item_name')
				totals['item_group'] = data[0].get('item_group')
				totals['disable_item_formatter'] = cint(self.show_item_name)

			if group_field in ('party', 'parent'):
				totals['customer_name'] = data[0].get("customer_name")
				totals['customer_group'] = data[0].get("customer_group")

		# Set reference field
		group_reference_doctypes = {
			"customer": "Customer",
			"parent": "Sales Invoice",
			"item_code": "Item",
		}

		reference_field = group_field[0] if isinstance(group_field, (list, tuple)) else group_field
		reference_dt = group_reference_doctypes.get(reference_field, unscrub(cstr(reference_field)))
		totals['doc_type'] = reference_dt
		totals['reference'] = grouped_by.get(reference_field) if group_field else "'Total'"

		if not group_field and self.group_by == [None]:
			totals['voucher_no'] = "'Total'"

		self.postprocess_row(totals)
		return totals

	def postprocess_row(self, item):
		item.revenue = item.base_net_amount - flt(item.get('base_returned_amount'))
		item.gross_profit = item.revenue - item.cogs
		item.per_gross_profit = item.gross_profit / item.revenue * 100 if item.revenue else 0

	def get_conditions(self):
		conditions = []

		if self.filters.company:
			conditions.append("si.company = %(company)s")

		if self.filters.from_date:
			conditions.append("si.posting_date >= %(from_date)s")
		if self.filters.to_date:
			conditions.append("si.posting_date <= %(to_date)s")

		if self.filters.get("sales_invoice"):
			conditions.append("si.name = %(sales_invoice)s")

		if self.filters.get("customer"):
			conditions.append("si.customer = %(customer)s")

		if self.filters.get("customer_group"):
			lft, rgt = frappe.db.get_value("Customer Group", self.filters.customer_group, ["lft", "rgt"])
			conditions.append("""c.customer_group in (select name from `tabCustomer Group`
					where lft>=%s and rgt<=%s)""" % (lft, rgt))

		if self.filters.get("territory"):
			lft, rgt = frappe.db.get_value("Territory", self.filters.territory, ["lft", "rgt"])
			conditions.append("""c.territory in (select name from `tabTerritory`
					where lft>=%s and rgt<=%s)""" % (lft, rgt))

		if self.filters.get("item_code"):
			conditions.append("si_item.item_code = %(item_code)s")

		if self.filters.get("item_group"):
			lft, rgt = frappe.db.get_value("Item Group", self.filters.item_group, ["lft", "rgt"])
			conditions.append("""i.item_group in (select name from `tabItem Group` 
					where lft>=%s and rgt<=%s)""" % (lft, rgt))

		if self.filters.get("brand"):
			conditions.append("i.brand = %(brand)s")

		if self.filters.get("item_source"):
			conditions.append("i.item_source=%(item_source)s")

		if self.filters.get("warehouse"):
			lft, rgt = frappe.db.get_value("Warehouse", self.filters.warehouse, ["lft", "rgt"])
			conditions.append("""si_item.warehouse in (select name from `tabWarehouse`
				where lft>=%s and rgt<=%s)""" % (lft, rgt))

		if self.filters.get("batch_no"):
			conditions.append("si_item.batch_no = %(batch_no)s")

		if self.filters.get("sales_person"):
			lft, rgt = frappe.db.get_value("Sales Person", self.filters.sales_person, ["lft", "rgt"])
			conditions.append("""sp.sales_person in (select name from `tabSales Person`
				where lft>=%s and rgt<=%s)""" % (lft, rgt))

		if not self.filters.get("include_non_stock_items"):
			conditions.append("i.is_stock_item = 1")

		return "and {}".format(" and ".join(conditions)) if conditions else ""

	def get_columns(self):
		columns = []
		group_list = [self.filters.group_by_1, self.filters.group_by_2, self.filters.group_by_3]

		show_party_name = False
		if frappe.defaults.get_global_default('cust_master_name') == "Naming Series":
			show_party_name = True

		customer_field = {
			"label": _("Customer"),
			"fieldtype": "Link",
			"fieldname": "customer",
			"options": "Customer",
			"width": 80 if show_party_name else 180
		}
		customer_name_field = {
			"label": _("Customer Name"),
			"fieldtype": "Data",
			"fieldname": "customer_name",
			"width": 180
		}
		item_code_field = {
			"label": _("Item Code"),
			"fieldtype": "Link",
			"fieldname": "item_code",
			"options": "Item",
			"width": 100 if self.show_item_name else 150
		}
		item_name_field = {
			"label": _("Item Name"),
			"fieldtype": "Data",
			"fieldname": "item_name",
			"width": 150
		}

		if len(self.group_by) > 1:
			columns += [
				{
					"label": _("Reference"),
					"fieldtype": "Dynamic Link",
					"fieldname": "reference",
					"options": "doc_type",
					"width": 180
				},
				{
					"label": _("Type"),
					"fieldtype": "Data",
					"fieldname": "doc_type",
					"width": 100
				},
			]

			if "Group by Item" in group_list:
				columns.append(item_name_field)

			columns += [
				{
					"label": _("Date"),
					"fieldtype": "Date",
					"fieldname": "posting_date",
					"width": 80
				},
			]

			if "Group by Customer" not in group_list:
				columns.append(customer_field)
				columns.append(customer_name_field)

			if "Group by Invoice" not in group_list:
				columns.append({
					"label": _("Sales Invoice"),
					"fieldtype": "Link",
					"fieldname": "parent",
					"options": "Sales Invoice",
					"width": 100
				})
		else:
			columns += [
				{
					"label": _("Date"),
					"fieldtype": "Date",
					"fieldname": "posting_date",
					"width": 80
				},
				{
					"label": _("Sales Invoice"),
					"fieldtype": "Link",
					"fieldname": "parent",
					"options": "Sales Invoice",
					"width": 100
				},
				customer_field,
				customer_name_field,
				item_code_field,
				item_name_field,
			]

		columns += [
			{
				"label": _("Net Qty"),
				"fieldtype": "Float",
				"fieldname": "cogs_qty",
				"width": 80
			},
			{
				"label": _("UOM"),
				"fieldtype": "Link",
				"options": "UOM",
				"fieldname": "uom",
				"width": 50
			},
			{
				"label": _("Split %"),
				"fieldtype": "Percent",
				"fieldname": "split_percentage",
				"width": 60
			},
			{
				"label": _("Valuation Rate"),
				"fieldtype": "Currency",
				"fieldname": "valuation_rate",
				"options": "Company:company:default_currency",
				"width": 110
			},
			{
				"label": _("Cost / Unit"),
				"fieldtype": "Currency",
				"fieldname": "cogs_per_unit",
				"options": "Company:company:default_currency",
				"width": 110
			},
			{
				"label": _("Revenue"),
				"fieldtype": "Currency",
				"fieldname": "revenue",
				"options": "Company:company:default_currency",
				"width": 110
			},
			{
				"label": _("Total Cost"),
				"fieldtype": "Currency",
				"fieldname": "cogs",
				"options": "Company:company:default_currency",
				"width": 110
			},
			{
				"label": _("Gross Profit"),
				"fieldtype": "Currency",
				"fieldname": "gross_profit",
				"options": "Company:company:default_currency",
				"width": 110
			},
			{
				"label": _("Profit / Unit"),
				"fieldtype": "Currency",
				"fieldname": "gross_profit_per_unit",
				"options": "Company:company:default_currency",
				"width": 110
			},
			{
				"label": _("Gross Profit %"),
				"fieldtype": "Percent",
				"fieldname": "per_gross_profit",
				"width": 110
			},
			{
				"label": _("Warehouse"),
				"fieldtype": "Link",
				"fieldname": "warehouse",
				"options": "Warehouse",
				"width": 100
			},
			{
				"label": _("Sales Person"),
				"fieldtype": "Data",
				"fieldname": "sales_person",
				"width": 150
			},
			{
				"label": _("Batch No"),
				"fieldtype": "Link",
				"fieldname": "batch_no",
				"options": "Batch",
				"width": 140
			},
			{
				"label": _("Invoice Qty"),
				"fieldtype": "Float",
				"fieldname": "qty",
				"width": 100
			},
			{
				"label": _("Returned Qty"),
				"fieldtype": "Float",
				"fieldname": "returned_qty",
				"width": 100
			},
			{
				"label": _("Net Amount"),
				"fieldtype": "Currency",
				"fieldname": "base_net_amount",
				"options": "Company:company:default_currency",
				"width": 110
			},
			{
				"label": _("Credit Amount"),
				"fieldtype": "Currency",
				"fieldname": "base_returned_amount",
				"options": "Company:company:default_currency",
				"width": 110
			},
		]
		if self.filters.sales_person:
			columns.append({
				"label": _("% Contribution"),
				"fieldtype": "Percent",
				"fieldname": "allocated_percentage",
				"width": 60
			})

		if not self.show_item_name:
			columns = [c for c in columns if c.get('fieldname') != 'item_name']
		if not show_party_name:
			columns = [c for c in columns if c.get('fieldname') != 'customer_name']

		return columns






def update_item_valuation_rates(items, doc=None):
	from frappe.model.document import Document

	if not doc:
		doc = frappe._dict()

	args = items
	if doc:
		args = []
		doc_dict = doc.as_dict() if isinstance(doc, Document) else doc
		for d in items:
			cur_arg = doc_dict.copy()
			cur_arg.update(d.as_dict() if isinstance(d, Document) else d)
			args.append(d)

	incoming_rate_data = get_item_incoming_rate_data(args)

	for i, d in enumerate(items):
		source_info = incoming_rate_data.source_map.get(i)
		if source_info:
			source_type, source_key = source_info
			source_object = incoming_rate_data.get(source_type)

			if source_object:
				d.valuation_rate = flt(source_object.get(source_key))
			else:
				d.valuation_rate = 0
		else:
			d.valuation_rate = 0


def get_item_incoming_rate_data(args):
	"""
	args list:
		'dt' or 'parenttype' or 'doctype'
		'child_docname' or 'name'
		'doc_status' or 'docstatus'
		'item_code'
		'batch_no'
		'update_stock'
		'dn_detail'
	"""

	source_map = {}

	item_codes = list(set([d.get('item_code') for d in args if d.get('item_code')]))
	stock_item_codes = get_stock_items(item_codes)

	for i, d in enumerate(args):
		if not d.get('item_code'):
			continue

		parent_doctype = d.get('dt') or d.get('parenttype') or d.get('doctype')
		row_name = d.get('child_docname') or d.get('name')
		docstatus = d.get('doc_status') or d.get('docstatus')

		if d.get('item_code') in stock_item_codes and parent_doctype in ('Sales Invoice', 'Delivery Note'):
			if d.get('dn_detail') and parent_doctype == "Sales Invoice":
				voucher_detail_no = ('Delivery Note', d.get('dn_detail'))
				source_map[i] = ('sle_outgoing_rate', voucher_detail_no)
			elif docstatus == 1:
				if row_name and (parent_doctype == "Delivery Note" or d.get('update_stock')):
					voucher_detail_no = (parent_doctype, row_name)
					source_map[i] = ('sle_outgoing_rate', voucher_detail_no)
			else:
				# get_incoming_rate
				source_map[i] = (None, None)
		else:
			transaction_date = getdate(d.get('transaction_date') or d.get('posting_date') or d.get('date'))
			source_map[i] = ('item_last_purchase_rate', (d.get('item_code'), transaction_date))

	last_purchase_rate_item_dates = list(set([key for obj, key in source_map.values() if obj == 'item_last_purchase_rate']))
	voucher_detail_nos = [key for obj, key in source_map.values() if obj == 'sle_outgoing_rate']

	out = frappe._dict()
	out.sle_outgoing_rate = get_sle_outgoing_rate(voucher_detail_nos)
	out.item_last_purchase_rate = get_item_last_purchase_rate(last_purchase_rate_item_dates)
	out.source_map = source_map
	return out


def get_item_last_purchase_rate(args):
	from erpnext.stock.doctype.item.item import get_last_purchase_details
	out = {}
	if not args:
		return out

	for item_code, t_date in args:
		get_last_purchase_detail = get_last_purchase_details(item_code, transaction_date=t_date)
		out[(item_code, t_date)] = get_last_purchase_detail['base_net_rate'] if get_last_purchase_detail else 0

	return out


def get_sle_outgoing_rate(voucher_detail_nos):
	out = {}
	if not voucher_detail_nos:
		return out

	values = []
	for voucher_type, voucher_detail_no in voucher_detail_nos:
		values.append(voucher_type)
		values.append(voucher_detail_no)

	res = frappe.db.sql("""
		select sum(stock_value_difference) / sum(actual_qty) as outgoing_rate, voucher_type, voucher_detail_no
		from `tabStock Ledger Entry`
		where (voucher_type, voucher_detail_no) in ({0})
		group by voucher_type, voucher_detail_no
	""".format(", ".join(["(%s, %s)"] * len(voucher_detail_nos))), values, as_dict=1)

	for d in res:
		out[(d.voucher_type, d.voucher_detail_no)] = d.outgoing_rate

	return out


def get_stock_items(item_codes):
	stock_items = []
	if item_codes:
		stock_items = frappe.db.sql_list("""
			select name from `tabItem` where name in %s and is_stock_item=1
		""", [item_codes])

	return stock_items
