import json

import frappe
from six import iteritems

from erpnext.demo.domains import data


def setup_data():
	setup_item()
	setup_item_price()
	frappe.db.commit()
	frappe.clear_cache()


def setup_item():
	items = json.loads(open(frappe.get_app_path("erpnext", "demo", "data", "item.json")).read())
	for i in items:
		if not i.get("domain") == "Retail":
			continue
		item = frappe.new_doc("Item")
		item.update(i)
		if hasattr(item, "item_defaults") and item.item_defaults[0].default_warehouse:
			item.item_defaults[0].company = data.get("Retail").get("company_name")
			warehouse = frappe.get_all(
				"Warehouse", filters={"warehouse_name": item.item_defaults[0].default_warehouse}, limit=1
			)
			if warehouse:
				item.item_defaults[0].default_warehouse = warehouse[0].name
		item.insert()


def setup_item_price():
	frappe.db.sql("delete from `tabItem Price`")

	standard_selling = {
		"OnePlus 6": 579,
		"OnePlus 6T": 600,
		"Xiaomi Poco F1": 300,
		"Iphone XS": 999,
		"Samsung Galaxy S9": 720,
		"Sony Bluetooth Headphone": 99,
		"Xiaomi Phone Repair": 10,
		"Samsung Phone Repair": 20,
		"OnePlus Phone Repair": 15,
		"Apple Phone Repair": 30,
	}

	standard_buying = {
		"OnePlus 6": 300,
		"OnePlus 6T": 350,
		"Xiaomi Poco F1": 200,
		"Iphone XS": 600,
		"Samsung Galaxy S9": 500,
		"Sony Bluetooth Headphone": 69,
	}

	for price_list in ("standard_buying", "standard_selling"):
		for item, rate in iteritems(locals().get(price_list)):
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"price_list": price_list.replace("_", " ").title(),
					"item_code": item,
					"selling": 1 if price_list == "standard_selling" else 0,
					"buying": 1 if price_list == "standard_buying" else 0,
					"price_list_rate": rate,
					"currency": "USD",
				}
			).insert()
