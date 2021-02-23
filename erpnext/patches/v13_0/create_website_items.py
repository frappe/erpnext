from __future__ import unicode_literals
import frappe

from erpnext.e_commerce.doctype.website_item.website_item import make_website_item

def execute():
	frappe.reload_doc("e_commerce", "doctype", "website_item")
	frappe.reload_doc("stock", "doctype", "item")

	web_fields_to_map = ["route", "slideshow", "website_image", "website_image_alt",
		"website_warehouse", "web_long_description", "website_content"]

	items = frappe.db.sql("""
		Select
			item_code, item_name, item_group, stock_uom, brand, image,
			has_variants, variant_of, description, weightage,
			route, slideshow, website_image_alt,
			website_warehouse, web_long_description, website_content
		from
			`tabItem`
		where
			show_in_website = 1
			or show_variant_in_website = 1""", as_dict=1)

	for item in items:
		if frappe.db.exists("Website Item", {"item_code": item.item_code}):
			continue

		# make website item from item (publish item)
		website_item = make_website_item(item, save=False)
		website_item.ranking = item.get("weightage")
		for field in web_fields_to_map:
			website_item.update({field: item.get(field)})
			website_item.save()

		# move Website Item Group & Website Specification table to Website Item
		for doc in ("Website Item Group", "Item Website Specification"):
			frappe.db.sql("""Update `tab{doctype}`
				set
					parenttype = 'Website Item',
					parent = '{web_item}'
				where
					parenttype = 'Item'
					and parent = '{item}'
				""".format(doctype=doc, web_item=website_item.name, item=item.item_code))