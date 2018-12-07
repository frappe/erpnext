# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import getdate, flt, cint
from six import iteritems
from erpnext.accounts.utils import get_fiscal_year

def execute(filters=None):
	return Analytics(filters).run()

class Analytics(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.date_field = 'transaction_date' \
			if self.filters.doc_type in ['Sales Order', 'Purchase Order'] else 'posting_date'
		self.months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
		self.get_period_date_ranges()
		self.entity_names = {}

	def run(self):
		self.get_columns()
		self.get_data()
		self.get_chart_data()
		return self.columns, self.data , None, self.chart

	def get_columns(self):
		self.columns = [{
			"label": _(self.filters.tree_type),
			"options": self.filters.tree_type,
			"fieldname": "entity",
			"fieldtype": "Link",
			"width": 140
		}]

		if self.filters.tree_type in ["Customer", "Supplier", "Item"]:
			self.columns.append({
				"label": _(self.filters.tree_type + " Name"),
				"fieldname": "entity_name",
				"fieldtype": "Data",
				"width": 140
			})

		self.columns.append({
			"label": _("Total"),
			"fieldname": "total",
			"fieldtype": "Float",
			"width": 110
		})

		for dummy, end_date in self.periodic_daterange:
			period = self.get_period(end_date)
			self.columns.append({
				"label": _(period),
				"fieldname": scrub(period),
				"fieldtype": "Float",
				"width": 110
			})

	def get_data(self):
		if self.filters.tree_type in ["Customer", "Supplier"]:
			self.get_entries("s." + scrub(self.filters.tree_type), "s." + scrub(self.filters.tree_type) + "_name")
			for d in self.entries:
				self.entity_names.setdefault(d.entity, d.entity_name)
			self.get_rows()

		elif self.filters.tree_type == 'Item':
			self.get_entries("i.item_code", "i.item_name")
			for d in self.entries:
				self.entity_names.setdefault(d.entity, d.entity_name)
			self.get_rows()

		elif self.filters.tree_type in ["Customer Group", "Supplier Group", "Territory"]:
			if self.filters.tree_type == 'Customer Group':
				entity_field = "s.customer_group"
			elif self.filters.tree_type == 'Supplier Group':
				entity_field = "s.supplier"
				self.get_supplier_parent_child_map()
			else:
				entity_field = "s.territory"
			self.get_entries(entity_field)
			self.get_groups()
			self.get_rows_by_group()

		elif self.filters.tree_type == 'Item Group':
			self.get_entries("i.item_group")
			self.get_groups()
			self.get_rows_by_group()

		elif self.filters.tree_type == 'Brand':
			self.get_entries("i.brand")
			self.get_rows()

	def get_entries(self, entity_field, entity_name_field=None):
		if entity_name_field:
			additional_field = ", {0} as entity_name".format(entity_name_field)
		else:
			additional_field = ""

		self.entries = frappe.db.sql("""
			select {entity_field} as entity, i.{value_field} as value_field, s.{date_field} {additional_field}
			from `tab{doctype} Item` i, `tab{doctype}` s
			where s.name = i.parent and i.docstatus = 1 and s.company = %s
			and s.{date_field} between %s and %s
		""".format(
			entity_field=entity_field,
			value_field=frappe.db.escape(self.filters.value_field),
			date_field=self.date_field,
			additional_field=additional_field,
			doctype=self.filters.doc_type),
		(self.filters.company, self.filters.from_date, self.filters.to_date), as_dict=1)

	def get_rows(self):
		self.data=[]
		self.get_periodic_data()

		for entity, period_data in iteritems(self.entity_periodic_data):
			row = {
				"entity": entity,
				"entity_name": self.entity_names.get(entity)
			}
			total = 0
			for dummy, end_date in self.periodic_daterange:
				period = self.get_period(end_date)
				amount = flt(period_data.get(period, 0.0))
				row[scrub(period)] = amount
				total += amount

			row["total"] = total
			self.data.append(row)

	def get_rows_by_group(self):
		self.get_periodic_data()
		out = []

		for d in reversed(self.group_entries):
			row = {
				"entity": d.name,
				"indent": self.depth_map.get(d.name)
			}
			total = 0
			for dummy, end_date in self.periodic_daterange:
				period = self.get_period(end_date)
				amount = flt(self.entity_periodic_data.get(d.name, {}).get(period, 0.0))
				row[scrub(period)] = amount
				if d.parent:
					self.entity_periodic_data.setdefault(d.parent, frappe._dict()).setdefault(period, 0.0)
					self.entity_periodic_data[d.parent][period] += amount
				total += amount
			row["total"] = total
			out = [row] + out
		self.data = out

	def get_periodic_data(self):
		self.entity_periodic_data = frappe._dict()

		for d in self.entries:
			if self.filters.tree_type == "Supplier Group":
				d.entity = self.parent_child_map.get(d.entity)
			period = self.get_period(d.get(self.date_field))
			self.entity_periodic_data.setdefault(d.entity, frappe._dict()).setdefault(period, 0.0)
			self.entity_periodic_data[d.entity][period] += flt(d.value_field)

	def get_period(self, posting_date):
		if self.filters.range == 'Weekly':
			period = "Week " + str(posting_date.isocalendar()[1]) + " " + str(posting_date.year)
		elif self.filters.range == 'Monthly':
			period = str(self.months[posting_date.month - 1]) + " " + str(posting_date.year)
		elif self.filters.range == 'Quarterly':
			period = "Quarter " + str(((posting_date.month-1)//3)+1) +" " + str(posting_date.year)
		else:
			year = get_fiscal_year(posting_date, company=self.filters.company)
			period = str(year[2])

		return period

	def get_period_date_ranges(self):
		from dateutil.relativedelta import relativedelta
		from_date, to_date = getdate(self.filters.from_date), getdate(self.filters.to_date)

		increment = {
			"Monthly": 1,
			"Quarterly": 3,
			"Half-Yearly": 6,
			"Yearly": 12
		}.get(self.filters.range, 1)

		self.periodic_daterange = []
		for dummy in range(1, 53, increment):
			if self.filters.range == "Weekly":
				period_end_date = from_date + relativedelta(days=6)
			else:
				period_end_date = from_date + relativedelta(months=increment, days=-1)

			if period_end_date > to_date:
				period_end_date = to_date
			self.periodic_daterange.append([from_date, period_end_date])

			from_date = period_end_date + relativedelta(days=1)
			if period_end_date == to_date:
				break

	def get_groups(self):
		if self.filters.tree_type == "Territory":
			parent = 'parent_territory'
		if self.filters.tree_type == "Customer Group":
			parent = 'parent_customer_group'
		if self.filters.tree_type == "Item Group":
			parent = 'parent_item_group'
		if self.filters.tree_type == "Supplier Group":
			parent = 'parent_supplier_group'

		self.depth_map = frappe._dict()

		self.group_entries = frappe.db.sql("""select name, lft, rgt , {parent} as parent
			from `tab{tree}` order by lft"""
			.format(tree=self.filters.tree_type, parent=parent), as_dict=1)

		for d in self.group_entries:
			if d.parent:
				self.depth_map.setdefault(d.name, self.depth_map.get(d.parent) + 1)
			else:
				self.depth_map.setdefault(d.name, 0)

	def get_supplier_parent_child_map(self):
		self.parent_child_map = frappe._dict(frappe.db.sql(""" select name, supplier_group from `tabSupplier`"""))

	def get_chart_data(self):
		length = len(self.columns)
		labels = [d.get("label") for d in self.columns[2:length-1]]
		self.chart = {
			"data": {
				'labels': labels,
				'datasets':[]
			},
			"type": "line"
		}