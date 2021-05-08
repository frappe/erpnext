# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import getdate, flt, add_to_date, add_days, cstr
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition
from erpnext.accounts.utils import get_fiscal_year
from six import iteritems

def execute(filters=None):
	return VehicleBookingAnalytics(filters).run()

class VehicleBookingAnalytics(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
		self.get_period_date_ranges()
		self.entity_names = {}

		self.filters.tree_doctype = self.get_tree_doctype()

		if not self.filters.get("company"):
			self.filters["company"] = frappe.db.get_single_value('Global Defaults', 'default_company')
		self.company_currency = frappe.get_cached_value('Company', self.filters.get("company"), "default_currency")

	def run(self):
		self.get_columns()
		self.get_data()
		self.get_chart_data()
		return self.columns, self.data, None, self.chart

	def get_columns(self):
		self.columns = [{
			"label": _(self.filters.tree_type),
			"options": self.filters.tree_doctype,
			"fieldname": "entity",
			"fieldtype": "Link",
			"width": 140
		}]

		show_name = False
		if self.filters.tree_type == "Customer":
			if frappe.defaults.get_global_default('cust_master_name') == "Naming Series":
				show_name = True
		if self.filters.tree_type in ("Variant", "Model"):
			if frappe.defaults.get_global_default('item_naming_by') != "Item Name":
				show_name = True

		if show_name:
			self.columns.append({
				"label": _(self.filters.tree_type + " Name"),
				"fieldname": "entity_name",
				"fieldtype": "Data",
				"width": 180
			})

		self.columns.append({
			"label": _("Total"),
			"fieldname": "total",
			"fieldtype": "Float",
			"width": 120
		})

		for end_date in self.periodic_daterange:
			period = self.get_period(end_date)
			self.columns.append({
				"label": _(period),
				"fieldname": scrub(period),
				"fieldtype": "Float",
				"period_column": True,
				"width": 120
			})

	def get_data(self):
		if self.filters.tree_type == 'Customer':
			self.get_entries("m.customer", "m.customer_name")
			self.get_rows()

		elif self.filters.tree_type == 'Variant':
			self.get_entries("m.item_code", "m.item_name")
			self.get_rows()

		elif self.filters.tree_type == 'Model':
			self.get_entries("item.variant_of")
			self.get_rows()

		elif self.filters.tree_type == 'Brand':
			self.get_entries("item.brand")
			self.get_rows()

		elif self.filters.tree_type == 'Vehicle Color':
			self.get_entries("m.vehicle_color")
			self.set_vehicle_color()
			self.get_rows()

		elif self.filters.tree_type in ["Item Group", "Sales Person"]:
			if self.filters.tree_type == 'Item Group':
				entity_field = "item.item_group"
			else:
				entity_field = "sp.sales_person"

			self.get_entries(entity_field)
			self.get_groups()
			self.get_rows_by_group()

	def get_entries(self, entity_field, entity_name_field=None):
		filter_conditions = self.get_conditions()

		include_sales_person = self.filters.tree_type == "Sales Person" or self.filters.sales_person
		sales_team_join = "left join `tabSales Team` sp on sp.parent = m.name and sp.parenttype = 'Vehicle Booking Order'" \
			if include_sales_person else ""

		include_supplier = self.filters.tree_type == "Supplier Group" or self.filters.supplier_group
		supplier_join = "inner join `tabSupplier` sup on sup.name = m.supplier" if include_supplier else ""

		entity_name_field = "{0} as entity_name, ".format(entity_name_field) if entity_name_field else ""
		if include_sales_person:
			value_field = "{0} * ifnull(sp.allocated_percentage, 100) / 100".format(self.get_value_fieldname())
		else:
			value_field = self.get_value_fieldname()

		include_delivery_period = self.filters.date_type == "Delivery Period"
		delivery_period_join = "left join `tabVehicle Allocation Period` dp on dp.name = m.delivery_period" \
			if include_delivery_period else ""

		color_fields = ""
		if self.filters.tree_type == "Vehicle Color":
			color_fields = "m.color_1, m.color_2, m.color_3, "

		self.entries = frappe.db.sql("""
			select
				{entity_field} as entity,
				{entity_name_field}
				{color_fields}
				{value_field} as value_field,
				{date_field} as date
			from `tabVehicle Booking Order` m
			left join `tabItem` item on item.name = m.item_code
			{supplier_join}
			{sales_team_join}
			{delivery_period_join}
			where m.docstatus = 1
				and {date_field} between %(from_date)s and %(to_date)s
				{filter_conditions}
		""".format(
			entity_field=entity_field,
			entity_name_field=entity_name_field,
			value_field=value_field,
			date_field=self.date_field,
			sales_team_join=sales_team_join,
			supplier_join=supplier_join,
			delivery_period_join=delivery_period_join,
			color_fields=color_fields,
			filter_conditions=filter_conditions
		), self.filters, as_dict=1)

		if entity_name_field:
			for d in self.entries:
				self.entity_names.setdefault(d.entity, d.entity_name)

	def set_vehicle_color(self):
		for d in self.entries:
			d.entity = d.entity or d.color_1 or d.color_2 or d.color_3

	def get_value_fieldname(self):
		filter_to_field = {
			"Units": "1",
			"Invoice Total": "invoice_total",
		}
		return filter_to_field.get(self.filters.value_field, "1")

	def get_value_fieldtype(self):
		filter_to_field = {
			"Units": "Float",
			"Invoice Total": "Currency",
		}
		return filter_to_field.get(self.filters.value_field, "Float")

	def get_tree_doctype(self):
		if self.filters.tree_type in ('Variant', 'Model'):
			return 'Item'
		else:
			return self.filters.tree_type

	def get_conditions(self):
		conditions = []

		self.date_field = 'm.transaction_date'
		if self.filters.date_type == "Vehicle Delivered Date":
			conditions.append('m.vehicle_delivered_date between %(from_date)s and %(to_date)s')
			self.date_field = 'm.vehicle_delivered_date'
		elif self.filters.date_type == "Delivery Period":
			conditions.append('((dp.from_date <= %(to_date)s) and (dp.to_date >= %(from_date)s))')
			self.date_field = 'dp.to_date'
		else:
			conditions.append('m.transaction_date between %(from_date)s and %(to_date)s')

		if self.filters.company:
			conditions.append("m.company = %(company)s")

		if self.filters.variant_of:
			conditions.append("item.variant_of = %(variant_of)s")

		if self.filters.item_code:
			conditions.append("item.name = %(item_code)s")

		if self.filters.vehicle_color:
			conditions.append("(m.vehicle_color = %(vehicle_color)s or (m.color_1 = %(vehicle_color)s and ifnull(m.vehicle_color, '') = ''))")

		if self.filters.item_group:
			conditions.append(get_item_group_condition(self.filters.item_group))

		if self.filters.brand:
			conditions.append("item.brand = %(brand)s")

		if self.filters.customer:
			conditions.append("m.customer = %(customer)s")

		if self.filters.financer:
			conditions.append("m.financer = %(financer)s")

		if self.filters.supplier:
			conditions.append("m.supplier = %(supplier)s")

		if self.filters.priority:
			conditions.append("m.priority = 1")

		if self.filters.get("sales_person"):
			lft, rgt = frappe.db.get_value("Sales Person", self.filters.sales_person, ["lft", "rgt"])
			conditions.append("""sp.sales_person in (select name from `tabSales Person`
					where lft>=%s and rgt<=%s and docstatus<2)""" % (lft, rgt))

		return "and {}".format(" and ".join(conditions)) if conditions else ""

	def get_rows(self):
		self.data = []
		self.get_periodic_data()

		total_row = frappe._dict({"entity": _("'Total'"), "total": 0})
		self.data.append(total_row)

		for entity, period_data in iteritems(self.entity_periodic_data):
			row = {
				"entity": entity,
				"entity_name": self.entity_names.get(entity),
				"indent": 1
			}
			total = 0
			for end_date in self.periodic_daterange:
				period = self.get_period(end_date)
				amount = flt(period_data.get(period, 0.0))
				row[scrub(period)] = amount
				total += amount

				total_row.setdefault(scrub(period), 0.0)
				total_row[scrub(period)] += amount
				total_row["total"] += amount

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
			for end_date in self.periodic_daterange:
				period = self.get_period(end_date)
				amount = flt(self.entity_periodic_data.get(d.name, {}).get(period, 0.0))
				row[scrub(period)] = amount
				if d.parent and (self.filters.tree_type != "Order Type" or d.parent == "Order Types"):
					self.entity_periodic_data.setdefault(d.parent, frappe._dict()).setdefault(period, 0.0)
					self.entity_periodic_data[d.parent][period] += amount
				total += amount
			row["total"] = total
			out = [row] + out
		self.data = out

	def get_periodic_data(self):
		self.entity_periodic_data = frappe._dict()

		for d in self.entries:
			period = self.get_period(d.get('date'))
			self.entity_periodic_data.setdefault(d.entity, frappe._dict()).setdefault(period, 0.0)
			self.entity_periodic_data[d.entity][period] += flt(d.value_field)

	def get_period(self, posting_date):
		if self.filters.range == 'Weekly':
			period = "Week " + str(posting_date.isocalendar()[1]) + " " + str(posting_date.year)
		elif self.filters.range == 'Monthly':
			period = str(self.months[posting_date.month - 1]) + " " + str(posting_date.year)
		elif self.filters.range == 'Quarterly':
			period = "Quarter " + str(((posting_date.month - 1) // 3) + 1) + " " + str(posting_date.year)
		else:
			year = get_fiscal_year(posting_date, company=self.filters.company)
			period = str(year[0])
		return period

	def get_period_date_ranges(self):
		from dateutil.relativedelta import relativedelta, MO
		from_date, to_date = getdate(self.filters.from_date), getdate(self.filters.to_date)

		increment = {
			"Monthly": 1,
			"Quarterly": 3,
			"Half-Yearly": 6,
			"Yearly": 12
		}.get(self.filters.range, 1)

		if self.filters.range in ['Monthly', 'Quarterly']:
			from_date = from_date.replace(day=1)
		elif self.filters.range == "Yearly":
			from_date = get_fiscal_year(from_date)[1]
		else:
			from_date = from_date + relativedelta(from_date, weekday=MO(-1))

		self.periodic_daterange = []
		for dummy in range(1, 53):
			if self.filters.range == "Weekly":
				period_end_date = add_days(from_date, 6)
			else:
				period_end_date = add_to_date(from_date, months=increment, days=-1)

			if period_end_date > to_date:
				period_end_date = to_date

			self.periodic_daterange.append(period_end_date)

			from_date = add_days(period_end_date, 1)
			if period_end_date == to_date:
				break

	def get_groups(self):
		if self.filters.tree_type == "Item Group":
			parent = 'parent_item_group'
		if self.filters.tree_type == "Sales Person":
			parent = 'parent_sales_person'

		self.depth_map = frappe._dict()

		self.group_entries = frappe.db.sql("""select name, lft, rgt , {parent} as parent
			from `tab{tree}` order by lft"""
		.format(tree=self.filters.tree_type, parent=parent), as_dict=1)

		for d in self.group_entries:
			if d.parent:
				self.depth_map.setdefault(d.name, self.depth_map.get(d.parent) + 1)
			else:
				self.depth_map.setdefault(d.name, 0)

	def get_chart_data(self):
		labels = [d.get("label") for d in self.columns if d.get("period_column")]
		self.chart = {
			"data": {
				'labels': labels,
				'datasets': []
			},
			"type": "line",
			"fieldtype": self.get_value_fieldtype()
		}

		if self.chart.get("fieldtype") == "Currency":
			self.chart['options'] = self.company_currency
