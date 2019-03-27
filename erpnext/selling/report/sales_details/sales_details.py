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
		columns = [
			{
				"label": _("Reference"),
				"fieldtype": "Dynamic Link",
				"fieldname": "reference",
				"options": "doctype",
				"width": 300
			},
			{
				"label": _("Name"),
				"fieldtype": "Data",
				"fieldname": "reference_name",
				"width": 150
			},
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
				"fieldname": "total_tax_amount",
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

		columns += [
			{
				"label": _("Grand Total"),
				"fieldtype": "Currency",
				"fieldname": "grand_total",
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
		self.get_itemsed_taxes()
		self.build_tree()

		data = []
		self.total_row["indent"] = 0
		self.total_row["_collapsed"] = True
		self.postprocess_row(self.total_row)
		data.append(self.total_row)

		for party, docs in iteritems(self.tree):
			party_row = self.party_totals[party]
			self.postprocess_row(party_row)
			party_row["indent"] = 1
			data.append(party_row)

			for docname, items_uoms in iteritems(docs):
				doc_row = self.doc_totals[docname]
				self.postprocess_row(doc_row)
				doc_row["indent"] = 2
				data.append(doc_row)

				for item_code, uom in items_uoms:
					item_row = self.doc_item_uom_totals[(docname, item_code, uom)]
					self.postprocess_row(item_row)
					item_row["indent"] = 3
					data.append(item_row)

		return data

	def build_tree(self):
		# Totals Row Template
		total_fields = ['qty', 'base_net_amount', 'base_amount']
		totals_template = {"currency": self.company_currency}
		for f in total_fields:
			totals_template[f] = 0.0
		for f in self.tax_amount_fields + self.tax_rate_fields:
			totals_template[f] = 0.0
		for f in self.tax_rate_fields:
			totals_template[f+"_count"] = 0

		# Containers
		self.tree = OrderedDict()
		self.party_totals = {}
		self.doc_totals = {}
		self.doc_item_uom_totals = {}
		self.total_row = {"reference": _("'Total'")}
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
					"reference": d.party,
					"reference_name": d.party_name,
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
					"reference": d.parent
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
					"reference": d.item_code,
					"reference_name": d.item_name,
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

			for f, tax in zip(self.tax_amount_fields, self.tax_columns):
				tax_amount = self.itemsed_tax.get(d.name, {}).get(tax, {}).get("tax_amount", 0.0)
				party_row[f] += tax_amount
				doc_row[f] += tax_amount
				item_row[f] += tax_amount
				self.total_row[f] += tax_amount
			for f, tax in zip(self.tax_rate_fields, self.tax_columns):
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

	def get_itemsed_taxes(self):
		if self.entries:
			self.itemsed_tax, self.tax_columns = get_tax_accounts(self.entries, [], self.company_currency, self.filters.doctype,
				"Sales Taxes and Charges" if self.filters.party_type == "Customer" else "Purchase Taxes and Charges")
			self.tax_amount_fields = ["tax_" + scrub(tax) for tax in self.tax_columns]
			self.tax_rate_fields = ["tax_" + scrub(tax) + "_rate" for tax in self.tax_columns]
		else:
			self.itemsed_tax, self.tax_columns = {}, []
			self.tax_amount_fields, self.tax_rate_fields = [], []

	def postprocess_row(self, row):
		# Calculate rate
		rate_fields = [
			('base_net_rate', 'base_net_amount'),
			('base_rate', 'base_amount')
		]
		if flt(row['qty']):
			for target, source in rate_fields:
				row[target] = flt(row[source]) / flt(row['qty'])

		# Calculate total taxes and grand total
		row["total_tax_amount"] = 0.0
		for f in self.tax_amount_fields:
			row["total_tax_amount"] += row[f]

		row["grand_total"] = row["base_net_amount"] + row["total_tax_amount"]

		# Calculate tax rates by averaging
		for f in self.tax_rate_fields:
			row[f] = row.get(f, 0.0)
			if row[f + "_count"]:
				row[f] /= row[f + "_count"]

			del row[f + "_count"]

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

def execute(filters=None):
	return SalesPurchaseDetailsReport(filters).run("Customer")
