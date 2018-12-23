# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint
from frappe.utils import flt
from erpnext.accounting.utils import get_fiscal_year
from erpnext.controllers.trends import get_period_date_ranges, get_period_month_ranges

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns(filters)
	period_month_ranges = get_period_month_ranges(filters["period"], filters["fiscal_year"])
	sim_map = get_salesperson_item_month_map(filters)

	data = []
	for salesperson, salesperson_items in sim_map.items():
		for item_group, monthwise_data in salesperson_items.items():
			row = [salesperson, item_group]
			totals = [0, 0, 0]
			for relevant_months in period_month_ranges:
				period_data = [0, 0, 0]
				for month in relevant_months:
					month_data = monthwise_data.get(month, {})
					for i, fieldname in enumerate(["target", "achieved", "variance"]):
						value = flt(month_data.get(fieldname))
						period_data[i] += value
						totals[i] += value
				period_data[2] = period_data[0] - period_data[1]
				row += period_data
			totals[2] = totals[0] - totals[1]
			row += totals
			data.append(row)

	return columns, sorted(data, key=lambda x: (x[0], x[1]))

def get_columns(filters):
	for fieldname in ["fiscal_year", "period", "target_on"]:
		if not filters.get(fieldname):
			label = (" ".join(fieldname.split("_"))).title()
			msgprint(_("Please specify") + ": " + label,
				raise_exception=True)

	columns = [_("Sales Person") + ":Link/Sales Person:120", _("Item Group") + ":Link/Item Group:120"]

	group_months = False if filters["period"] == "Monthly" else True

	for from_date, to_date in get_period_date_ranges(filters["period"], filters["fiscal_year"]):
		for label in [_("Target") + " (%s)", _("Achieved") + " (%s)", _("Variance") + " (%s)"]:
			if group_months:
				label = label % (_(from_date.strftime("%b")) + " - " + _(to_date.strftime("%b")))
			else:
				label = label % _(from_date.strftime("%b"))

			columns.append(label+":Float:120")

	return columns + [_("Total Target") + ":Float:120", _("Total Achieved") + ":Float:120",
		_("Total Variance") + ":Float:120"]

#Get sales person & item group details
def get_salesperson_details(filters):
	return frappe.db.sql("""
		select
			sp.name, td.item_group, td.target_qty, td.target_amount, sp.distribution_id
		from
			`tabSales Person` sp, `tabTarget Detail` td
		where
			td.parent=sp.name and td.fiscal_year=%s order by sp.name
		""", (filters["fiscal_year"]), as_dict=1)

#Get target distribution details of item group
def get_target_distribution_details(filters):
	target_details = {}

	for d in frappe.db.sql("""
		select
			md.name, mdp.month, mdp.percentage_allocation
		from
			`tabMonthly Distribution Percentage` mdp, `tabMonthly Distribution` md
		where
			mdp.parent=md.name and md.fiscal_year=%s
		""", (filters["fiscal_year"]), as_dict=1):
			target_details.setdefault(d.name, {}).setdefault(d.month, flt(d.percentage_allocation))

	return target_details

#Get achieved details from sales order
def get_achieved_details(filters, sales_person, all_sales_persons, target_item_group, item_groups):
	start_date, end_date = get_fiscal_year(fiscal_year = filters["fiscal_year"])[1:]

	item_details = frappe.db.sql("""
		SELECT st.sales_person, MONTHNAME(so.transaction_date) as month_name,
		CASE
			WHEN so.status = "Closed" THEN sum(soi.delivered_qty * soi.conversion_factor * (st.allocated_percentage/100))
			ELSE sum(soi.stock_qty * (st.allocated_percentage/100))
		END as qty,
		CASE
			WHEN so.status = "Closed" THEN sum(soi.delivered_qty * soi.conversion_factor * soi.base_net_rate * (st.allocated_percentage/100))
			ELSE sum(soi.base_net_amount * (st.allocated_percentage/100))
		END as amount
		from
			`tabSales Order Item` soi, `tabSales Order` so, `tabSales Team` st
		where
			soi.parent=so.name and so.docstatus=1 and st.parent=so.name
			and so.transaction_date>=%s and so.transaction_date<=%s
			and exists(SELECT name from `tabSales Person` where lft >= %s and rgt <= %s and name=st.sales_person)
			and exists(SELECT name from `tabItem Group` where lft >= %s and rgt <= %s and name=soi.item_group)
		group by
			sales_person, month_name
			""",
		(start_date, end_date, all_sales_persons[sales_person].lft, all_sales_persons[sales_person].rgt,
			item_groups[target_item_group].lft, item_groups[target_item_group].rgt), as_dict=1)

	actual_details = {}
	for d in item_details:
		actual_details.setdefault(d.month_name, frappe._dict({
			"quantity" : 0,
			"amount" : 0
		}))

		value_dict = actual_details[d.month_name]
		value_dict.quantity += flt(d.qty)
		value_dict.amount += flt(d.amount)

	return actual_details

def get_salesperson_item_month_map(filters):
	import datetime
	salesperson_details = get_salesperson_details(filters)
	tdd = get_target_distribution_details(filters)
	item_groups = get_item_groups()
	sales_persons = get_sales_persons()

	sales_person_achievement_dict = {}
	for sd in salesperson_details:
		achieved_details = get_achieved_details(filters, sd.name, sales_persons, sd.item_group, item_groups)

		for month_id in range(1, 13):
			month = datetime.date(2013, month_id, 1).strftime('%B')
			sales_person_achievement_dict.setdefault(sd.name, {}).setdefault(sd.item_group, {})\
					.setdefault(month, frappe._dict({
							"target": 0.0, "achieved": 0.0
						}))

			sales_target_achieved = sales_person_achievement_dict[sd.name][sd.item_group][month]
			month_percentage = tdd.get(sd.distribution_id, {}).get(month, 0) \
				if sd.distribution_id else 100.0/12

			if (filters["target_on"] == "Quantity"):
				sales_target_achieved.target = flt(sd.target_qty) * month_percentage / 100
			else:
				sales_target_achieved.target = flt(sd.target_amount) * month_percentage / 100

			sales_target_achieved.achieved = achieved_details.get(month, frappe._dict())\
				.get(filters["target_on"].lower())

	return sales_person_achievement_dict

def get_item_groups():
	item_groups = frappe._dict()
	for d in frappe.get_all("Item Group", fields=["name", "lft", "rgt"]):
		item_groups.setdefault(d.name, frappe._dict({
			"lft": d.lft,
			"rgt": d.rgt
		}))
	return item_groups

def get_sales_persons():
	sales_persons = frappe._dict()
	for d in frappe.get_all("Sales Person", fields=["name", "lft", "rgt"]):
		sales_persons.setdefault(d.name, frappe._dict({
			"lft": d.lft,
			"rgt": d.rgt
		}))
	return sales_persons
