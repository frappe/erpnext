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
		if self.filters.view == "Tree":
			columns = [
				{
					"label": _("Reference"),
					"fieldtype": "Dynamic Link",
					"fieldname": "reference",
					"options": "doc_type",
					"width": 300
				},
				{
					"label": _("Type"),
					"fieldtype": "Data",
					"fieldname": "doc_type",
					"width": 110
				},
				{
					"label": _("Date"),
					"fieldtype": "Date",
					"fieldname": "date",
					"width": 80
				},
			]
		else:
			columns = [
				{
					"label": _("Date"),
					"fieldtype": "Date",
					"fieldname": "date",
					"width": 80
				},
				{
					"label": _("Voucher No"),
					"fieldtype": "Link",
					"fieldname": "voucher_no",
					"options": self.filters.doctype,
					"width": 140
				},
				{
					"label": _(self.filters.party_type),
					"fieldtype": "Link",
					"fieldname": "party",
					"options": self.filters.party_type,
					"width": 150
				},
				{
					"label": _("Item"),
					"fieldtype": "Link",
					"fieldname": "item_code",
					"options": "Item",
					"width": 150
				},
			]

		columns += [
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
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _("Net Amount"),
				"fieldtype": "Currency",
				"fieldname": "base_net_amount",
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _("Taxes and Charges"),
				"fieldtype": "Currency",
				"fieldname": "total_tax_amount",
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _("Grand Total"),
				"fieldtype": "Currency",
				"fieldname": "grand_total",
				"options": "Company:company:default_currency",
				"width": 120
			},
		]

		if self.filters.include_taxes:
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
						"options": "Company:company:default_currency",
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
		]

		return columns

	def get_data(self):
		self.get_entries()
		self.get_itemised_taxes()
		self.prepare_data()

		data = []

		if self.filters.view == "Tree":
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
		else:
			for item in self.item_list:
				self.postprocess_row(item)
			data = self.item_list

		return data

	def prepare_data(self):
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
		self.item_list = []
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

			if self.filters.view == "Tree":
				# Add tree nodes if not already there
				self.tree.setdefault(d.party, OrderedDict())\
					.setdefault(d.parent, set())\
					.add((d.item_code, d.uom))

				# Party total row
				if d.party not in self.party_totals:
					party_row = self.party_totals[d.party] = totals_template.copy()
					party_row.update({
						"doc_type": self.filters.party_type,
						"reference": d.party,
						scrub(self.filters.party_type) + "_name": d.party_name,
						"party_name": d.party_name,
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
						"doc_type": self.filters.doctype,
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
					"uom": d.uom,
					"group": d.item_group,
					"group_doctype": "Item Group",
					"brand": d.brand
				})
				if self.filters.view == "Tree":
					item_row.update({
						"doc_type": "Item",
						"reference": d.item_code,
						"item_name": d.item_name,
					})
				else:
					item_row.update({
						"voucher_no": d.parent,
						"party": d.party,
						"party_name": d.party_name,
						scrub(self.filters.party_type) + "_name": d.party_name,
						"item_code": d.item_code,
						"item_name": d.item_name
					})

				if self.filters.party_type == "Customer":
					item_row.update({
						"sales_person": d.sales_person,
						"territory": d.territory
					})

				if self.filters.view != "Tree":
					self.item_list.append(item_row)

			else:
				item_row = self.doc_item_uom_totals[(d.parent, d.item_code, d.uom)]

			# Group totals
			for f in total_fields:
				item_row[f] += d[f]
				if self.filters.view == "Tree":
					party_row[f] += d[f]
					doc_row[f] += d[f]
					self.total_row[f] += d[f]

			for f, tax in zip(self.tax_amount_fields, self.tax_columns):
				tax_amount = self.itemised_tax.get(d.name, {}).get(tax, {}).get("tax_amount", 0.0)
				item_row[f] += tax_amount
				if self.filters.view == "Tree":
					doc_row[f] += tax_amount
					party_row[f] += tax_amount
					self.total_row[f] += tax_amount
			for f, tax in zip(self.tax_rate_fields, self.tax_columns):
				tax_rate = self.itemised_tax.get(d.name, {}).get(tax, {}).get("tax_rate", 0.0)
				if tax_rate:
					item_row[f] += tax_rate
					item_row[f+"_count"] += 1
					if self.filters.view == "Tree":
						doc_row[f] += tax_rate
						doc_row[f+"_count"] += 1
						party_row[f] += tax_rate
						party_row[f+"_count"] += 1
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
			order by s.{date_field}, s.{party_field}, s.name, i.item_code
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

		if self.filters.party_type == "Customer" and self.filters.view == "Tree":
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

	def get_itemised_taxes(self):
		if self.entries:
			self.itemised_tax, self.tax_columns = get_tax_accounts(self.entries, [], self.company_currency, self.filters.doctype,
				"Sales Taxes and Charges" if self.filters.party_type == "Customer" else "Purchase Taxes and Charges")
			self.tax_amount_fields = ["tax_" + scrub(tax) for tax in self.tax_columns]
			self.tax_rate_fields = ["tax_" + scrub(tax) + "_rate" for tax in self.tax_columns]
		else:
			self.itemised_tax, self.tax_columns = {}, []
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
