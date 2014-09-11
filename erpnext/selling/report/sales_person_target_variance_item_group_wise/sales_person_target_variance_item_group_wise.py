# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint
from frappe.utils import flt
from erpnext.accounts.utils import get_fiscal_year
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
	return frappe.db.sql("""select sp.name, td.item_group, td.target_qty,
		td.target_amount, sp.distribution_id
		from `tabSales Person` sp, `tabTarget Detail` td
		where td.parent=sp.name and td.fiscal_year=%s order by sp.name""",
		(filters["fiscal_year"]), as_dict=1)

#Get target distribution details of item group
def get_target_distribution_details(filters):
	target_details = {}

	for d in frappe.db.sql("""select bd.name, bdd.month, bdd.percentage_allocation
		from `tabBudget Distribution Detail` bdd, `tabBudget Distribution` bd
		where bdd.parent=bd.name and bd.fiscal_year=%s""", (filters["fiscal_year"]), as_dict=1):
			target_details.setdefault(d.name, {}).setdefault(d.month, flt(d.percentage_allocation))

	return target_details

#Get achieved details from sales order
def get_achieved_details(filters):
	start_date, end_date = get_fiscal_year(fiscal_year = filters["fiscal_year"])[1:]

	item_details = frappe.db.sql("""select soi.item_code, soi.qty, soi.base_amount, so.transaction_date,
		st.sales_person, MONTHNAME(so.transaction_date) as month_name
		from `tabSales Order Item` soi, `tabSales Order` so, `tabSales Team` st
		where soi.parent=so.name and so.docstatus=1 and
		st.parent=so.name and so.transaction_date>=%s and
		so.transaction_date<=%s""" % ('%s', '%s'),
		(start_date, end_date), as_dict=1)

	item_actual_details = {}
	for d in item_details:
		item_actual_details.setdefault(d.sales_person, {}).setdefault(\
			get_item_group(d.item_code), []).append(d)

	return item_actual_details

def get_salesperson_item_month_map(filters):
	import datetime
	salesperson_details = get_salesperson_details(filters)
	tdd = get_target_distribution_details(filters)
	achieved_details = get_achieved_details(filters)

	sim_map = {}
	for sd in salesperson_details:
		for month_id in range(1, 13):
			month = datetime.date(2013, month_id, 1).strftime('%B')
			sim_map.setdefault(sd.name, {}).setdefault(sd.item_group, {})\
				.setdefault(month, frappe._dict({
					"target": 0.0, "achieved": 0.0
				}))

			tav_dict = sim_map[sd.name][sd.item_group][month]
			month_percentage = tdd.get(sd.distribution_id, {}).get(month, 0) \
				if sd.distribution_id else 100.0/12

			for ad in achieved_details.get(sd.name, {}).get(sd.item_group, []):
				if (filters["target_on"] == "Quantity"):
					tav_dict.target = flt(sd.target_qty) * month_percentage / 100
					if ad.month_name == month:
							tav_dict.achieved += ad.qty

				if (filters["target_on"] == "Amount"):
					tav_dict.target = flt(sd.target_amount) * month_percentage / 100
					if ad.month_name == month:
							tav_dict.achieved += ad.base_amount

	return sim_map

def get_item_group(item_name):
	return frappe.db.get_value("Item", item_name, "item_group")
