# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate, getdate, flt, add_days

def execute(filters=None):
	filters.day_before_from_date = add_days(filters.from_date, -1)
	columns, data = get_columns(filters), get_data(filters)
	return columns, data
	
def get_data(filters):
	data = []
	
	asset_categories = get_asset_categories(filters)
	assets = get_assets(filters)
	asset_costs = get_asset_costs(assets, filters)
	asset_depreciations = get_accumulated_depreciations(assets, filters)
	
	for asset_category in asset_categories:
		row = frappe._dict()
		row.asset_category = asset_category
		row.update(asset_costs.get(asset_category))

		row.cost_as_on_to_date = (flt(row.cost_as_on_from_date) + flt(row.cost_of_new_purchase)
			- flt(row.cost_of_sold_asset) - flt(row.cost_of_scrapped_asset))
			
		row.update(asset_depreciations.get(asset_category))
		row.accumulated_depreciation_as_on_to_date = (flt(row.accumulated_depreciation_as_on_from_date) + 
			flt(row.depreciation_amount_during_the_period) - flt(row.depreciation_eliminated))
		
		row.net_asset_value_as_on_from_date = (flt(row.cost_as_on_from_date) - 
			flt(row.accumulated_depreciation_as_on_from_date))
		
		row.net_asset_value_as_on_to_date = (flt(row.cost_as_on_to_date) - 
			flt(row.accumulated_depreciation_as_on_to_date))
	
		data.append(row)
		
	return data
	
def get_asset_categories(filters):
	return frappe.db.sql_list("""
		select distinct asset_category from `tabAsset` 
		where docstatus=1 and company=%s and purchase_date <= %s
	""", (filters.company, filters.to_date))
	
def get_assets(filters):
	return frappe.db.sql("""
		select name, asset_category, purchase_date, gross_purchase_amount, disposal_date, status
		from `tabAsset` 
		where docstatus=1 and company=%s and purchase_date <= %s""", 
		(filters.company, filters.to_date), as_dict=1)
		
def get_asset_costs(assets, filters):
	asset_costs = frappe._dict()
	for d in assets:
		asset_costs.setdefault(d.asset_category, frappe._dict({
			"cost_as_on_from_date": 0,
			"cost_of_new_purchase": 0,
			"cost_of_sold_asset": 0,
			"cost_of_scrapped_asset": 0
		}))
		
		costs = asset_costs[d.asset_category]
		
		if getdate(d.purchase_date) < getdate(filters.from_date):
			if not d.disposal_date or getdate(d.disposal_date) >= getdate(filters.from_date):
				costs.cost_as_on_from_date += flt(d.gross_purchase_amount)
		else:
			costs.cost_of_new_purchase += flt(d.gross_purchase_amount)
			
			if d.disposal_date and getdate(d.disposal_date) >= getdate(filters.from_date) \
					and getdate(d.disposal_date) <= getdate(filters.to_date):
				if d.status == "Sold":
					costs.cost_of_sold_asset += flt(d.gross_purchase_amount)
				elif d.status == "Scrapped":
					costs.cost_of_scrapped_asset += flt(d.gross_purchase_amount)
			
	return asset_costs
	
def get_accumulated_depreciations(assets, filters):
	asset_depreciations = frappe._dict()
	for d in assets:
		asset = frappe.get_doc("Asset", d.name)
		
		if d.asset_category in asset_depreciations:
			asset_depreciations[d.asset_category]['accumulated_depreciation_as_on_from_date'] += asset.opening_accumulated_depreciation
		else:
			asset_depreciations.setdefault(d.asset_category, frappe._dict({
				"accumulated_depreciation_as_on_from_date": asset.opening_accumulated_depreciation,
				"depreciation_amount_during_the_period": 0,
				"depreciation_eliminated_during_the_period": 0
			}))

		depr = asset_depreciations[d.asset_category]

		if not asset.schedules: # if no schedule,
			if asset.disposal_date:
				# and disposal is NOT within the period, then opening accumulated depreciation not included
				if getdate(asset.disposal_date) < getdate(filters.from_date) or getdate(asset.disposal_date) > getdate(filters.to_date):
					asset_depreciations[d.asset_category]['accumulated_depreciation_as_on_from_date'] = 0

				# if no schedule, and disposal is within period, accumulated dep is the amount eliminated
				if getdate(asset.disposal_date) >= getdate(filters.from_date) and getdate(asset.disposal_date) <= getdate(filters.to_date):
					depr.depreciation_eliminated_during_the_period += asset.opening_accumulated_depreciation
		
		for schedule in asset.get("schedules"):
			if getdate(schedule.schedule_date) < getdate(filters.from_date):
				if not asset.disposal_date or getdate(asset.disposal_date) >= getdate(filters.from_date):
					depr.accumulated_depreciation_as_on_from_date += flt(schedule.depreciation_amount)
			elif getdate(schedule.schedule_date) <= getdate(filters.to_date):
				if not asset.disposal_date:
					depr.depreciation_amount_during_the_period += flt(schedule.depreciation_amount)
				else:
					if getdate(schedule.schedule_date) <= getdate(asset.disposal_date):
						depr.depreciation_amount_during_the_period += flt(schedule.depreciation_amount)

			if asset.disposal_date and getdate(asset.disposal_date) >= getdate(filters.from_date) and getdate(asset.disposal_date) <= getdate(filters.to_date):
				if getdate(schedule.schedule_date) <= getdate(asset.disposal_date):
					depr.depreciation_eliminated_during_the_period += flt(schedule.depreciation_amount)
		
	return asset_depreciations
	
def get_columns(filters):
	return [
		{
			"label": _("Asset Category"),
			"fieldname": "asset_category",
			"fieldtype": "Link",
			"options": "Asset Category",
			"width": 120
		},
		{
			"label": _("Cost as on") + " " + formatdate(filters.day_before_from_date),
			"fieldname": "cost_as_on_from_date",
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"label": _("Cost of New Purchase"),
			"fieldname": "cost_of_new_purchase",
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"label": _("Cost of Sold Asset"),
			"fieldname": "cost_of_sold_asset",
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"label": _("Cost of Scrapped Asset"),
			"fieldname": "cost_of_scrapped_asset",
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"label": _("Cost as on") + " " + formatdate(filters.to_date),
			"fieldname": "cost_as_on_to_date",
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"label": _("Accumulated Depreciation as on") + " " + formatdate(filters.day_before_from_date),
			"fieldname": "accumulated_depreciation_as_on_from_date",
			"fieldtype": "Currency",
			"width": 270
		},
		{
			"label": _("Depreciation Amount during the period"),
			"fieldname": "depreciation_amount_during_the_period",
			"fieldtype": "Currency",
			"width": 240
		},
		{
			"label": _("Depreciation Eliminated due to disposal of assets"),
			"fieldname": "depreciation_eliminated_during_the_period",
			"fieldtype": "Currency",
			"width": 300
		},
		{
			"label": _("Accumulated Depreciation as on") + " " + formatdate(filters.to_date),
			"fieldname": "accumulated_depreciation_as_on_to_date",
			"fieldtype": "Currency",
			"width": 270
		},
		{
			"label": _("Net Asset value as on") + " " + formatdate(filters.day_before_from_date),
			"fieldname": "net_asset_value_as_on_from_date",
			"fieldtype": "Currency",
			"width": 200
		},
		{
			"label": _("Net Asset value as on") + " " + formatdate(filters.to_date),
			"fieldname": "net_asset_value_as_on_to_date",
			"fieldtype": "Currency",
			"width": 200
		}
	]
