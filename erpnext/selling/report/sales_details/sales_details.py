# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import getdate, nowdate, flt
from collections import OrderedDict
from erpnext.accounts.report.item_wise_sales_register.item_wise_sales_register import get_tax_accounts
from six import iteritems

class SalesPurchaseDetailsReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(self.filters.from_date or nowdate())
		self.filters.to_date = getdate(self.filters.to_date or nowdate())

		self.additional_customer_info = frappe._dict()

		self.date_field = 'transaction_date' \
			if self.filters.doctype in ['Sales Order', 'Purchase Order'] else 'posting_date'

		if not self.filters.get("company"):
			self.filters["company"] = frappe.db.get_single_value('Global Defaults', 'default_company')
		self.company_currency = frappe.get_cached_value('Company', self.filters.get("company"), "default_currency")

	def run(self, party_type):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("From Date must be before To Date"))

		self.filters.party_type = party_type

		data = self.get_data()
		columns = self.get_columns()
		return columns, data

	def get_columns(self):
		show_name = False
		if self.filters.tree_type == "Customer":
			if frappe.defaults.get_global_default('cust_master_name') == "Naming Series":
				show_name = True
		if self.filters.tree_type == "Supplier":
			if frappe.defaults.get_global_default('supp_master_name') == "Naming Series":
				show_name = True
		if frappe.defaults.get_global_default('item_naming_by') == "Naming Series":
			show_name = True

		columns = [
			{
				"label": _("Reference"),
				"fieldtype": "Dynamic Link",
				"fieldname": "docname",
				"options": "doctype",
				"width": 400
			}
		]

		if show_name:
			columns.append({
				"label": _("Name"),
				"fieldtype": "Data",
				"fieldname": "name",
				"width": 150
			})

		columns += [
			{
				"label": _("Type"),
				"fieldtype": "Data",
				"fieldname": "doctype",
				"width": 110
			},
			{
				"label": _("Date"),
				"fieldtype": "Date",
				"fieldname": "date",
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
				"label": _("Qty"),
				"fieldtype": "Float",
				"fieldname": "qty",
				"width": 90
			},
			{
				"label": _("Net Rate"),
				"fieldtype": "Currency",
				"fieldname": "base_net_rate",
				"options": "currency",
				"width": 120
			},
			{
				"label": _("Net Amount"),
				"fieldtype": "Currency",
				"fieldname": "base_net_amount",
				"options": "currency",
				"width": 120
			},
			{
				"label": _("Rate"),
				"fieldtype": "Currency",
				"fieldname": "base_rate",
				"options": "currency",
				"width": 120
			},
			{
				"label": _("Amount"),
				"fieldtype": "Currency",
				"fieldname": "base_amount",
				"options": "currency",
				"width": 120
			},
			{
				"label": _("Total Tax Amount"),
				"fieldtype": "Currency",
				"fieldname": "tax_total_amount",
				"options": "currency",
				"width": 120
			},
		]

		for tax_description in self.tax_columns:
			amount_field = "tax_" + scrub(tax_description)
			rate_field = amount_field + "_rate"
			columns += [
				{
					"label": _(tax_description) + " (%)",
					"fieldtype": "Percent",
					"fieldname": rate_field,
					"width": 60
				},
				{
					"label": _(tax_description),
					"fieldtype": "Currency",
					"fieldname": amount_field,
					"options": "currency",
					"width": 120
				},
			]

		if self.filters.party_type == "Customer":
			columns += [
				{
					"label": _("Sales Person"),
					"fieldtype": "Data",
					"fieldname": "sales_person",
					"width": 150
				},
				{
					"label": _("Territory"),
					"fieldtype": "Link",
					"fieldname": "territory",
					"options": "Territory",
					"width": 100
				},
			]

		columns += [
			{
				"label": _("Group"),
				"fieldtype": "Dynamic Link",
				"fieldname": "group",
				"options": "group_doctype",
				"width": 100
			},
			{
				"label": _("Brand"),
				"fieldtype": "Link",
				"fieldname": "brand",
				"options": "Brand",
				"width": 100
			},
			{
				"label": _("Currency"),
				"fieldtype": "Link",
				"fieldname": "currency",
				"options": "Currency",
				"width": 50
			},
		]

		return columns

	def get_data(self):
		self.get_entries()
		self.build_tree()

		data = []
		self.total_row["indent"] = 0
		self.total_row["_collapsed"] = True
		set_row_average_fields(self.total_row, self.tax_columns)
		data.append(self.total_row)

		for party, docs in iteritems(self.tree):
			party_row = self.party_totals[party]
			set_row_average_fields(party_row, self.tax_columns)
			party_row["indent"] = 1
			data.append(party_row)

			for docname, items_uoms in iteritems(docs):
				doc_row = self.doc_totals[docname]
				set_row_average_fields(doc_row, self.tax_columns)
				doc_row["indent"] = 2
				data.append(doc_row)

				for item_code, uom in items_uoms:
					item_row = self.doc_item_uom_totals[(docname, item_code, uom)]
					set_row_average_fields(item_row, self.tax_columns)
					item_row["indent"] = 3
					data.append(item_row)

		return data

	def build_tree(self):
		# Totals Row Template
		total_fields = ['qty', 'base_net_amount', 'base_amount']
		tax_amount_fields = ["tax_" + scrub(tax) for tax in self.tax_columns]
		tax_rate_fields = ["tax_" + scrub(tax) + "_rate" for tax in self.tax_columns]
		totals_template = {"currency": self.company_currency, "tax_total_amount": 0.0}
		for f in total_fields:
			totals_template[f] = 0.0
		for f in tax_amount_fields + tax_rate_fields:
			totals_template[f] = 0.0
		for f in tax_rate_fields:
			totals_template[f+"_count"] = 0

		# Containers
		self.tree = OrderedDict()
		self.party_totals = {}
		self.doc_totals = {}
		self.doc_item_uom_totals = {}
		self.total_row = {"docname": _("'Total'")}
		self.total_row.update(totals_template)

		# Build tree and group totals
		for d in self.entries:
			# Set UOM based on qty field
			if self.filters.qty_field == "Transaction Qty":
				d.uom = d.uom
			elif self.filters.qty_field == "Contents Qty":
				d.uom = d.alt_uom or d.stock_uom
			else:
				d.uom = d.stock_uom

			# Add tree nodes if not already there
			self.tree.setdefault(d.party, OrderedDict())\
				.setdefault(d.parent, set())\
				.add((d.item_code, d.uom))

			# Party total row
			if d.party not in self.party_totals:
				party_row = self.party_totals[d.party] = totals_template.copy()
				party_row.update({
					"doctype": self.filters.party_type,
					"docname": d.party,
					"name": d.party_name,
					"group": d.party_group,
					"group_doctype": d.party_group_dt
				})
				if self.filters.party_type == "Customer":
					details = self.additional_customer_info.get(d.party, frappe._dict())
					party_row.update({
						"sales_person": details.sales_person,
						"territory": details.territory
					})
			else:
				party_row = self.party_totals[d.party]

			# Document total row
			if d.parent not in self.doc_totals:
				doc_row = self.doc_totals[d.parent] = totals_template.copy()
				doc_row.update({
					"date": d.date,
					"doctype": self.filters.doctype,
					"docname": d.parent
				})
				if self.filters.party_type == "Customer":
					doc_row.update({
						"sales_person": d.sales_person,
						"territory": d.territory
					})
			else:
				doc_row = self.doc_totals[d.parent]

			# Doc-Item-UOM row
			if (d.parent, d.item_code, d.uom) not in self.doc_item_uom_totals:
				item_row = self.doc_item_uom_totals[(d.parent, d.item_code, d.uom)] = totals_template.copy()
				item_row.update({
					"date": d.date,
					"doctype": "Item",
					"docname": d.item_code,
					"name": d.item_name,
					"uom": d.uom,
					"group": d.item_group,
					"group_doctype": "Item Group",
					"brand": d.brand
				})
				if self.filters.party_type == "Customer":
					item_row.update({
						"sales_person": d.sales_person,
						"territory": d.territory
					})
			else:
				item_row = self.doc_item_uom_totals[(d.parent, d.item_code, d.uom)]

			for f in total_fields:
				party_row[f] += d[f]
				doc_row[f] += d[f]
				item_row[f] += d[f]
				self.total_row[f] += d[f]

			for f, tax in zip(tax_amount_fields, self.tax_columns):
				tax_amount = self.itemsed_tax.get(d.name, {}).get(tax, {}).get("tax_amount", 0.0)
				party_row[f] += tax_amount
				party_row["tax_total_amount"] += tax_amount
				doc_row[f] += tax_amount
				doc_row["tax_total_amount"] += tax_amount
				item_row[f] += tax_amount
				item_row["tax_total_amount"] += tax_amount
				self.total_row[f] += tax_amount
				self.total_row["tax_total_amount"] += tax_amount
			for f, tax in zip(tax_rate_fields, self.tax_columns):
				tax_rate = self.itemsed_tax.get(d.name, {}).get(tax, {}).get("tax_rate", 0.0)
				if tax_rate:
					party_row[f] += tax_rate
					party_row[f+"_count"] += 1
					doc_row[f] += tax_rate
					doc_row[f+"_count"] += 1
					item_row[f] += tax_rate
					item_row[f+"_count"] += 1
					self.total_row[f] += tax_rate
					self.total_row[f+"_count"] += 1

	def get_entries(self):
		party_field = scrub(self.filters.party_type)
		party_name_field = party_field + "_name"
		qty_field = self.get_qty_fieldname()

		sales_person_table = ", `tabSales Team` sp" if self.filters.party_type == "Customer" else ""
		sales_person_condition = "and sp.parent = s.name and sp.parenttype = %(doctype)s" if self.filters.party_type == "Customer" else ""
		sales_person_field = ", GROUP_CONCAT(DISTINCT sp.sales_person SEPARATOR ', ') as sales_person" if self.filters.party_type == "Customer" else ""

		supplier_table = ", `tabSupplier` sup" if self.filters.party_type == "Supplier" else ""
		supplier_condition = "and sup.name = s.supplier" if self.filters.party_type == "Supplier" else ""

		territory_field = ", s.territory" if self.filters.party_type == "Customer" else ""

		party_group_field = ", s.customer_group as party_group, 'Customer Group' as party_group_dt" if self.filters.party_type == "Customer"\
			else ", sup.supplier_group as party_group, 'Supplier Group' as party_group_dt"

		is_opening_condition = "and s.is_opening != 'Yes'" if self.filters.doctype in ['Sales Invoice', 'Purchase Invoice']\
			else ""

		filter_conditions = self.get_conditions()

		self.entries = frappe.db.sql("""
			select
				s.name as parent, i.name, s.{date_field} as date,
				s.{party_field} as party, s.{party_name_field} as party_name,
				i.item_code, i.item_name,
				i.{qty_field} as qty,
				i.uom, i.stock_uom, i.alt_uom,
				i.base_net_amount, i.base_amount,
				i.brand, i.item_group
				{party_group_field} {sales_person_field} {territory_field}
			from 
				`tab{doctype} Item` i, `tab{doctype}` s {sales_person_table} {supplier_table}
			where i.parent = s.name and s.docstatus = 1 and s.company = %(company)s
				and s.{date_field} between %(from_date)s and %(to_date)s
				{sales_person_condition} {supplier_condition} {is_opening_condition} {filter_conditions}
			group by s.name, i.name
			order by s.{date_field}
		""".format(
			party_field=party_field,
			party_name_field=party_name_field,
			party_group_field=party_group_field,
			territory_field=territory_field,
			qty_field=qty_field,
			date_field=self.date_field,
			doctype=self.filters.doctype,
			sales_person_field=sales_person_field,
			sales_person_table=sales_person_table,
			sales_person_condition=sales_person_condition,
			supplier_table=supplier_table,
			supplier_condition=supplier_condition,
			is_opening_condition=is_opening_condition,
			filter_conditions=filter_conditions
		), self.filters, as_dict=1)

		if self.filters.party_type == "Customer":
			additional_customer_info = frappe.db.sql("""
				select
					s.customer, GROUP_CONCAT(DISTINCT s.territory SEPARATOR ', ') as territory
					{sales_person_field}
				from 
					`tab{doctype} Item` i, `tab{doctype}` s {sales_person_table}
				where i.parent = s.name and s.docstatus = 1 and s.company = %(company)s 
					and sp.parent = s.name and sp.parenttype = %(doctype)s
					and s.{date_field} between %(from_date)s and %(to_date)s
					{sales_person_condition} {is_opening_condition} {filter_conditions}
				group by s.{party_field}
			""".format(
				party_field=party_field,
				date_field=self.date_field,
				doctype=self.filters.doctype,
				sales_person_field=sales_person_field,
				sales_person_table=sales_person_table,
				sales_person_condition=sales_person_condition,
				supplier_table=supplier_table,
				supplier_condition=supplier_condition,
				is_opening_condition=is_opening_condition,
				filter_conditions=filter_conditions
			), self.filters, as_dict=1)

			for d in additional_customer_info:
				self.additional_customer_info[d.customer] = d

		if self.entries:
			self.itemsed_tax, self.tax_columns = get_tax_accounts(self.entries, [], self.company_currency, self.filters.doctype,
				"Sales Taxes and Charges" if self.filters.party_type == "Customer" else "Purchase Taxes and Charges")
		else:
			self.itemsed_tax, self.tax_columns = {}, []

	def get_qty_fieldname(self):
		filter_to_field = {
			"Stock Qty": "stock_qty",
			"Contents Qty": "alt_uom_qty",
			"Transaction Qty": "qty"
		}
		return filter_to_field.get(self.filters.qty_field, "stock_qty")

	def get_conditions(self):
		conditions = []

		if self.filters.get("customer"):
			conditions.append("s.customer=%(customer)s")

		if self.filters.get("customer_group"):
			lft, rgt = frappe.db.get_value("Customer Group", self.filters.customer_group, ["lft", "rgt"])
			conditions.append("""s.customer_group in (select name from `tabCustomer Group`
					where lft>=%s and rgt<=%s and docstatus<2)""" % (lft, rgt))

		if self.filters.get("supplier"):
			conditions.append("s.supplier=%(supplier)s")

		if self.filters.get("supplier_group"):
			lft, rgt = frappe.db.get_value("Supplier Group", self.filters.supplier_group, ["lft", "rgt"])
			conditions.append("""sup.supplier_group in (select name from `tabSupplier Group`
					where lft>=%s and rgt<=%s and docstatus<2)""" % (lft, rgt))

		if self.filters.get("item_code"):
			conditions.append("i.item_code=%(item_code)s")

		if self.filters.get("item_group"):
			lft, rgt = frappe.db.get_value("Item Group", self.filters.item_group, ["lft", "rgt"])
			conditions.append("""i.item_group in (select name from `tabItem Group`
					where lft>=%s and rgt<=%s and docstatus<2)""" % (lft, rgt))

		if self.filters.get("brand"):
			conditions.append("i.brand=%(brand)s")

		if self.filters.get("territory"):
			lft, rgt = frappe.db.get_value("Territory", self.filters.territory, ["lft", "rgt"])
			conditions.append("""s.territory in (select name from `tabTerritory`
					where lft>=%s and rgt<=%s and docstatus<2)""" % (lft, rgt))

		if self.filters.get("sales_person"):
			lft, rgt = frappe.db.get_value("Sales Person", self.filters.sales_person, ["lft", "rgt"])
			conditions.append("""sp.sales_person in (select name from `tabSales Person`
					where lft>=%s and rgt<=%s and docstatus<2)""" % (lft, rgt))

		return "and {}".format(" and ".join(conditions)) if conditions else ""

def set_row_average_fields(row, tax_columns):
	if not flt(row['qty']):
		return

	fields = [
		('base_net_rate', 'base_net_amount'),
		('base_rate', 'base_amount')
	]
	for target, source in fields:
		row[target] = flt(row[source]) / flt(row['qty'])

	tax_rate_fields = ["tax_" + scrub(tax) + "_rate" for tax in tax_columns]
	for f in tax_rate_fields:
		row[f] = row.get(f, 0.0)
		if row[f+"_count"]:
			row[f] /= row[f+"_count"]

		del row[f+"_count"]

def execute(filters=None):
	return SalesPurchaseDetailsReport(filters).run("Customer")
