import frappe
import json
from six import iteritems

old_item_taxes = {}
item_tax_templates = {}
rename_template_to_untitled = []

def execute():
	for d in frappe.db.sql("""select parent as item_code, tax_type, tax_rate from `tabItem Tax`""", as_dict=1):
		old_item_taxes.setdefault(d.item_code, [])
		old_item_taxes[d.item_code].append(d)

	frappe.reload_doc("accounts", "doctype", "item_tax_template_detail")
	frappe.reload_doc("accounts", "doctype", "item_tax_template")
	frappe.reload_doc("stock", "doctype", "item")
	frappe.reload_doc("stock", "doctype", "item_tax")
	frappe.reload_doc("selling", "doctype", "quotation_item")
	frappe.reload_doc("selling", "doctype", "sales_order_item")
	frappe.reload_doc("stock", "doctype", "delivery_note_item")
	frappe.reload_doc("accounts", "doctype", "sales_invoice_item")
	frappe.reload_doc("buying", "doctype", "supplier_quotation_item")
	frappe.reload_doc("buying", "doctype", "purchase_order_item")
	frappe.reload_doc("stock", "doctype", "purchase_receipt_item")
	frappe.reload_doc("accounts", "doctype", "purchase_invoice_item")
	frappe.reload_doc("accounts", "doctype", "accounts_settings")

	# for each item that have item tax rates
	for item_code in old_item_taxes.keys():
		# make current item's tax map
		item_tax_map = {}
		for d in old_item_taxes[item_code]:
			item_tax_map[d.tax_type] = d.tax_rate

		item_tax_template_name = get_item_tax_template(item_tax_map, item_code)

		# update the item tax table
		item = frappe.get_doc("Item", item_code)
		item.set("taxes", [])
		item.append("taxes", {"item_tax_template": item_tax_template_name, "tax_category": ""})
		item.save()
	
	doctypes = [
		'Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice',
		'Supplier Quotation', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice'
	]
	for dt in doctypes:
		for d in frappe.db.sql("""select name, parent, item_code, item_tax_rate from `tab{0} Item`
								where ifnull(item_tax_rate, '') not in ('', '{{}}')""".format(dt), as_dict=1):
			item_tax_map = json.loads(d.item_tax_rate)
			item_tax_template = get_item_tax_template(item_tax_map, d.item_code, d.parent)
			frappe.db.set_value(dt + " Item", d.name, "item_tax_template", item_tax_template)

	idx = 1
	for oldname in rename_template_to_untitled:
		frappe.rename_doc("Item Tax Template", oldname, "Untitled {}".format(idx))
		idx += 1

	settings = frappe.get_single("Accounts Settings")
	settings.add_taxes_from_item_tax_template = 0
	settings.determine_address_tax_category_from = "Billing Address"
	settings.save()

def get_item_tax_template(item_tax_map, item_code, parent=None):
	# search for previously created item tax template by comparing tax maps
	for template, item_tax_template_map in iteritems(item_tax_templates):
		if item_tax_map == item_tax_template_map:
			if not parent:
				rename_template_to_untitled.append(template)
			return template

	# if no item tax template found, create one
	item_tax_template = frappe.new_doc("Item Tax Template")
	item_tax_template.title = "{}--{}".format(parent, item_code) if parent else "Item-{}".format(item_code)
	for tax_type, tax_rate in iteritems(item_tax_map):
		item_tax_template.append("taxes", {"tax_type": tax_type, "tax_rate": tax_rate})
		item_tax_templates.setdefault(item_tax_template.title, {})
		item_tax_templates[item_tax_template.title][tax_type] = tax_rate
	item_tax_template.save()
	return item_tax_template.name
