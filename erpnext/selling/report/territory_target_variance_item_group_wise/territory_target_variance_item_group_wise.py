# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint, scrub
from frappe.utils import flt
from erpnext.accounts.utils import get_fiscal_year
from erpnext.controllers.trends import get_period_date_ranges, get_period_month_ranges

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns(filters)
	period_month_ranges = get_period_month_ranges(filters["period"], filters["fiscal_year"])
	territory_item_group_dict = get_territory_item_month_map(filters)

	data = []
	for territory, territory_items in territory_item_group_dict.items():
		for item_group, monthwise_data in territory_items.items():
			row = [territory, item_group]
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
			msgprint(_("Please specify") + ": " + label, raise_exception=True)

	columns = [_("Territory") + ":Link/Territory:120", _("Item Group") + ":Link/Item Group:120"]

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

#Get territory & item group details
def get_territory_details(filters):
	return frappe.db.sql("""
		select
			t.name, td.item_group, td.target_qty, td.target_alt_uom_qty, td.target_amount, t.distribution_id
		from
			`tabTerritory` t, `tabTarget Detail` td
		where
			td.parent=t.name and td.fiscal_year=%s order by t.name
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
def get_achieved_details(filters, territory, all_territories, target_item_group, item_groups):
	start_date, end_date = get_fiscal_year(fiscal_year = filters["fiscal_year"])[1:]

	item_details = frappe.db.sql("""
		SELECT so.territory, MONTHNAME(so.transaction_date) as month_name,
		CASE
			WHEN so.status = "Closed" THEN sum(soi.delivered_qty * soi.conversion_factor)
			ELSE sum(soi.stock_qty)
		END as stock_qty,
		CASE
			WHEN so.status = "Closed" THEN sum(soi.delivered_qty * soi.conversion_factor * soi.alt_uom_size)
			ELSE sum(soi.alt_uom_qty)
		END as alt_uom_qty,
		CASE
			WHEN so.status = "Closed" THEN sum(soi.delivered_qty * soi.conversion_factor * soi.base_net_rate)
			ELSE sum(soi.base_net_amount)
		END as amount
		from
			`tabSales Order Item` soi, `tabSales Order` so
		where
			soi.parent=so.name and so.docstatus=1
			and so.transaction_date>=%s and so.transaction_date<=%s
			and exists(SELECT name from `tabTerritory` where lft >= %s and rgt <= %s and name=so.territory)
			and exists(SELECT name from `tabItem Group` where lft >= %s and rgt <= %s and name=soi.item_group)
		group by
			territory, month_name
			""",
		(start_date, end_date, all_territories[territory].lft, all_territories[territory].rgt,
			item_groups[target_item_group].lft, item_groups[target_item_group].rgt), as_dict=1)

	actual_details = {}
	for d in item_details:
		actual_details.setdefault(d.month_name, frappe._dict({
			"stock_qty" : 0,
			"contents_qty" : 0,
			"amount" : 0
		}))

		value_dict = actual_details[d.month_name]
		value_dict.stock_qty += flt(d.stock_qty)
		value_dict.contents_qty += flt(d.alt_uom_qty)
		value_dict.amount += flt(d.amount)

	return actual_details

def get_territory_item_month_map(filters):
	import datetime
	territory_details = get_territory_details(filters)
	tdd = get_target_distribution_details(filters)
	item_groups = get_item_groups()
	territories = get_territories()

	territory_achievement_dict = {}
	for sd in territory_details:
		achieved_details = get_achieved_details(filters, sd.name, territories, sd.item_group, item_groups)

		for month_id in range(1, 13):
			month = datetime.date(2013, month_id, 1).strftime('%B')
			territory_achievement_dict.setdefault(sd.name, {}).setdefault(sd.item_group, {})\
					.setdefault(month, frappe._dict({
							"target": 0.0, "achieved": 0.0
						}))

			sales_target_achieved = territory_achievement_dict[sd.name][sd.item_group][month]
			month_percentage = tdd.get(sd.distribution_id, {}).get(month, 0) \
				if sd.distribution_id else 100.0/12

			if filters["target_on"] == "Stock Qty":
				sales_target_achieved.target = flt(sd.target_qty) * month_percentage / 100
			elif filters["target_on"] == "Contents Qty":
				sales_target_achieved.target = flt(sd.target_alt_uom_qty) * month_percentage / 100
			else:
				sales_target_achieved.target = flt(sd.target_amount) * month_percentage / 100

			sales_target_achieved.achieved = achieved_details.get(month, frappe._dict())\
				.get(scrub(filters["target_on"]))

	return territory_achievement_dict

def get_item_groups():
	item_groups = frappe._dict()
	for d in frappe.get_all("Item Group", fields=["name", "lft", "rgt"]):
		item_groups.setdefault(d.name, frappe._dict({
			"lft": d.lft,
			"rgt": d.rgt
		}))
	return item_groups

def get_territories():
	territories = frappe._dict()
	for d in frappe.get_all("Territory", fields=["name", "lft", "rgt"]):
		territories.setdefault(d.name, frappe._dict({
			"lft": d.lft,
			"rgt": d.rgt
		}))
	return territories
