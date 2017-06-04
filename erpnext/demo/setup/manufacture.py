from __future__ import unicode_literals

import random, json
import frappe
from frappe.utils import nowdate, add_days
from erpnext.demo.setup.setup_data import import_json

def setup_data():
	import_json("Asset Category")
	setup_item()
	setup_workstation()
	setup_asset()
	import_json('Operation')
	setup_item_price()
	show_item_groups_in_website()
	import_json('BOM', submit=True)
	frappe.db.commit()
	frappe.clear_cache()

def setup_workstation():
	workstations = [u'Drilling Machine 1', u'Lathe 1', u'Assembly Station 1', u'Assembly Station 2', u'Packing and Testing Station']
	for w in workstations:
		frappe.get_doc({
			"doctype": "Workstation",
			"workstation_name": w,
			"holiday_list": frappe.get_all("Holiday List")[0].name,
			"hour_rate_consumable": int(random.random() * 20),
			"hour_rate_electricity": int(random.random() * 10),
			"hour_rate_labour": int(random.random() * 40),
			"hour_rate_rent": int(random.random() * 10),
			"working_hours": [
				{
					"enabled": 1,
				    "start_time": "8:00:00",
					"end_time": "15:00:00"
				}
			]
		}).insert()

def show_item_groups_in_website():
	"""set show_in_website=1 for Item Groups"""
	products = frappe.get_doc("Item Group", "Products")
	products.show_in_website = 1
	products.route = 'products'
	products.save()

def setup_asset():
	assets = json.loads(open(frappe.get_app_path('erpnext', 'demo', 'data', 'asset.json')).read())
	for d in assets:
		asset = frappe.new_doc('Asset')
		asset.update(d)
		asset.purchase_date = add_days(nowdate(), -random.randint(20, 1500))
		asset.next_depreciation_date = add_days(asset.purchase_date, 30)
		asset.warehouse = "Stores - WPL"
		asset.set_missing_values()
		asset.make_depreciation_schedule()
		asset.flags.ignore_validate = True
		asset.save()
		asset.submit()

def setup_item():
	items = json.loads(open(frappe.get_app_path('erpnext', 'demo', 'data', 'item.json')).read())
	for i in items:
		item = frappe.new_doc('Item')
		item.update(i)
		if item.default_warehouse:
			warehouse = frappe.get_all('Warehouse', filters={'warehouse_name': item.default_warehouse}, limit=1)
			if warehouse:
				item.default_warehouse = warehouse[0].name
		item.insert()

def setup_product_bundle():
	frappe.get_doc({
		'doctype': 'Product Bundle',
		'new_item_code': 'Wind Mill A Series with Spare Bearing',
		'items': [
			{'item_code': 'Wind Mill A Series', 'qty': 1},
			{'item_code': 'Bearing Collar', 'qty': 1},
			{'item_code': 'Bearing Assembly', 'qty': 1},
		]
	}).insert()

def setup_item_price():
	frappe.db.sql("delete from `tabItem Price`")

	standard_selling = {
		"Base Bearing Plate": 28,
		"Base Plate": 21,
		"Bearing Assembly": 300,
		"Bearing Block": 14,
		"Bearing Collar": 103.6,
		"Bearing Pipe": 63,
		"Blade Rib": 46.2,
		"Disc Collars": 42,
		"External Disc": 56,
		"Internal Disc": 70,
		"Shaft": 340,
		"Stand": 400,
		"Upper Bearing Plate": 300,
		"Wind Mill A Series": 320,
		"Wind Mill A Series with Spare Bearing": 750,
		"Wind MIll C Series": 400,
		"Wind Turbine": 400,
		"Wing Sheet": 30.8
	}

	standard_buying = {
		"Base Bearing Plate": 20,
		"Base Plate": 28,
		"Base Plate Un Painted": 16,
		"Bearing Block": 13,
		"Bearing Collar": 96.4,
		"Bearing Pipe": 55,
		"Blade Rib": 38,
		"Disc Collars": 34,
		"External Disc": 50,
		"Internal Disc": 60,
		"Shaft": 250,
		"Stand": 300,
		"Upper Bearing Plate": 200,
		"Wing Sheet": 25
	}

	for price_list in ("standard_buying", "standard_selling"):
		for item, rate in locals().get(price_list).iteritems():
			frappe.get_doc({
				"doctype": "Item Price",
				"price_list": price_list.replace("_", " ").title(),
				"item_code": item,
				"selling": 1 if price_list=="standard_selling" else 0,
				"buying": 1 if price_list=="standard_buying" else 0,
				"price_list_rate": rate,
				"currency": "USD"
			}).insert()
