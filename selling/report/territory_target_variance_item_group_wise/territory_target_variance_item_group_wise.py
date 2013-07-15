# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes import _, msgprint
from webnotes.utils import flt
import time
from accounts.utils import get_fiscal_year
from controllers.trends import get_period_date_ranges, get_period_month_ranges

def execute(filters=None):
	if not filters: filters = {}
	
	columns = get_columns(filters)
	period_month_ranges = get_period_month_ranges(filters["period"], filters["fiscal_year"])
	tim_map = get_territory_item_month_map(filters)

	precision = webnotes.conn.get_value("Global Defaults", None, "float_precision") or 2

	data = []

	for territory, territory_items in tim_map.items():
		for item_group, monthwise_data in territory_items.items():
			row = [territory, item_group]
			totals = [0, 0, 0]
			for relevant_months in period_month_ranges:
				period_data = [0, 0, 0]
				for month in relevant_months:
					month_data = monthwise_data.get(month, {})
					for i, fieldname in enumerate(["target", "achieved", "variance"]):
						value = flt(month_data.get(fieldname), precision)
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

	columns = ["Territory:Link/Territory:80", "Item Group:Link/Item Group:80"]

	group_months = False if filters["period"] == "Monthly" else True

	for from_date, to_date in get_period_date_ranges(filters["period"], filters["fiscal_year"]):
		for label in ["Target (%s)", "Achieved (%s)", "Variance (%s)"]:
			if group_months:
				columns.append(label % (from_date.strftime("%b") + " - " + to_date.strftime("%b")))				
			else:
				columns.append(label % from_date.strftime("%b"))

	return columns + ["Total Target::80", "Total Achieved::80", "Total Variance::80"]

#Get territory & item group details
def get_territory_details(filters):
	return webnotes.conn.sql("""select t.name, td.item_group, td.target_qty, 
		td.target_amount, t.distribution_id 
		from `tabTerritory` t, `tabTarget Detail` td 
		where td.parent=t.name and td.fiscal_year=%s and 
		ifnull(t.distribution_id, '')!='' order by t.name""", 
		(filters["fiscal_year"]), as_dict=1)

#Get target distribution details of item group
def get_target_distribution_details(filters):
	target_details = {}

	for d in webnotes.conn.sql("""select bdd.month, bdd.percentage_allocation \
		from `tabBudget Distribution Detail` bdd, `tabBudget Distribution` bd, \
		`tabTerritory` t where bdd.parent=bd.name and t.distribution_id=bd.name and \
		bd.fiscal_year=%s""", (filters["fiscal_year"]), as_dict=1):
			target_details.setdefault(d.month, d)

	return target_details

#Get achieved details from sales order
def get_achieved_details(filters):
	start_date, end_date = get_fiscal_year(fiscal_year = filters["fiscal_year"])[1:]

	return webnotes.conn.sql("""select soi.item_code, soi.qty, soi.amount, so.transaction_date, 
		so.territory, MONTHNAME(so.transaction_date) as month_name 
		from `tabSales Order Item` soi, `tabSales Order` so 
		where soi.parent=so.name and so.docstatus=1 and so.transaction_date>=%s and 
		so.transaction_date<=%s""" % ('%s', '%s'), 
		(start_date, end_date), as_dict=1)

def get_territory_item_month_map(filters):
	territory_details = get_territory_details(filters)
	tdd = get_target_distribution_details(filters)
	achieved_details = get_achieved_details(filters)

	tim_map = {}

	for td in territory_details:
		for month in tdd:
			tim_map.setdefault(td.name, {}).setdefault(td.item_group, {})\
			.setdefault(month, webnotes._dict({
				"target": 0.0, "achieved": 0.0
			}))

			tav_dict = tim_map[td.name][td.item_group][month]

			for ad in achieved_details:
				if (filters["target_on"] == "Quantity"):
					tav_dict.target = flt(td.target_qty) * \
						(tdd[month]["percentage_allocation"]/100)
					if ad.month_name == month and get_item_group(ad.item_code) == td.item_group \
						and ad.territory == td.name:
							tav_dict.achieved += ad.qty

				if (filters["target_on"] == "Amount"):
					tav_dict.target = flt(td.target_amount) * \
						(tdd[month]["percentage_allocation"]/100)
					if ad.month_name == month and get_item_group(ad.item_code) == td.item_group \
						and ad.territory == td.name:
							tav_dict.achieved += ad.amount

	return tim_map

def get_item_group(item_name):
	return webnotes.conn.get_value("Item", item_name, "item_group")