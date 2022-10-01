# Copyright (c) 2015, ESS and contributors
# For license information, please see license.txt


import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.rename_doc import rename_doc


class LabTestTemplate(Document):
	def after_insert(self):
		if not self.item:
			create_item_from_template(self)

	def validate(self):
		if self.is_billable and (not self.lab_test_rate or self.lab_test_rate <= 0.0):
			frappe.throw(_("Standard Selling Rate should be greater than zero."))

		self.validate_conversion_factor()
		self.enable_disable_item()

	def on_update(self):
		# If change_in_item update Item and Price List
		if self.change_in_item and self.is_billable and self.item:
			self.update_item()
			item_price = self.item_price_exists()
			if not item_price:
				if self.lab_test_rate and self.lab_test_rate > 0.0:
					price_list_name = frappe.db.get_value(
						"Selling Settings", None, "selling_price_list"
					) or frappe.db.get_value("Price List", {"selling": 1})
					make_item_price(self.lab_test_code, price_list_name, self.lab_test_rate)
			else:
				frappe.db.set_value("Item Price", item_price, "price_list_rate", self.lab_test_rate)

			self.db_set("change_in_item", 0)

		elif not self.is_billable and self.item:
			frappe.db.set_value("Item", self.item, "disabled", 1)

		self.reload()

	def on_trash(self):
		# Remove template reference from item and disable item
		if self.item:
			try:
				item = self.item
				self.db_set("item", "")
				frappe.delete_doc("Item", item)
			except Exception:
				frappe.throw(_("Not permitted. Please disable the Lab Test Template"))

	def enable_disable_item(self):
		if self.is_billable:
			if self.disabled:
				frappe.db.set_value("Item", self.item, "disabled", 1)
			else:
				frappe.db.set_value("Item", self.item, "disabled", 0)

	def update_item(self):
		item = frappe.get_doc("Item", self.item)
		if item:
			item.update(
				{
					"item_name": self.lab_test_name,
					"item_group": self.lab_test_group,
					"disabled": 0,
					"standard_rate": self.lab_test_rate,
					"description": self.lab_test_description,
				}
			)
			item.flags.ignore_mandatory = True
			item.save(ignore_permissions=True)

	def item_price_exists(self):
		item_price = frappe.db.exists({"doctype": "Item Price", "item_code": self.lab_test_code})
		if item_price:
			return item_price[0][0]
		return False

	def validate_conversion_factor(self):
		if self.lab_test_template_type == "Single" and self.secondary_uom and not self.conversion_factor:
			frappe.throw(_("Conversion Factor is mandatory"))
		if self.lab_test_template_type == "Compound":
			for item in self.normal_test_templates:
				if item.secondary_uom and not item.conversion_factor:
					frappe.throw(_("Row #{0}: Conversion Factor is mandatory").format(item.idx))
		if self.lab_test_template_type == "Grouped":
			for group in self.lab_test_groups:
				if (
					group.template_or_new_line == "Add New Line"
					and group.secondary_uom
					and not group.conversion_factor
				):
					frappe.throw(_("Row #{0}: Conversion Factor is mandatory").format(group.idx))


def create_item_from_template(doc):
	uom = frappe.db.exists("UOM", "Unit") or frappe.db.get_single_value("Stock Settings", "stock_uom")
	# Insert item
	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": doc.lab_test_code,
			"item_name": doc.lab_test_name,
			"item_group": doc.lab_test_group,
			"description": doc.lab_test_description,
			"is_sales_item": 1,
			"is_service_item": 1,
			"is_purchase_item": 0,
			"is_stock_item": 0,
			"include_item_in_manufacturing": 0,
			"show_in_website": 0,
			"is_pro_applicable": 0,
			"disabled": 0 if doc.is_billable and not doc.disabled else doc.disabled,
			"stock_uom": uom,
		}
	).insert(ignore_permissions=True, ignore_mandatory=True)

	# Insert item price
	if doc.is_billable and doc.lab_test_rate != 0.0:
		price_list_name = frappe.db.get_value(
			"Selling Settings", None, "selling_price_list"
		) or frappe.db.get_value("Price List", {"selling": 1})
		if doc.lab_test_rate:
			make_item_price(item.name, price_list_name, doc.lab_test_rate)
		else:
			make_item_price(item.name, price_list_name, 0.0)
	# Set item in the template
	frappe.db.set_value("Lab Test Template", doc.name, "item", item.name)

	doc.reload()


def make_item_price(item, price_list_name, item_price):
	frappe.get_doc(
		{
			"doctype": "Item Price",
			"price_list": price_list_name,
			"item_code": item,
			"price_list_rate": item_price,
		}
	).insert(ignore_permissions=True, ignore_mandatory=True)


@frappe.whitelist()
def change_test_code_from_template(lab_test_code, doc):
	doc = frappe._dict(json.loads(doc))

	if frappe.db.exists({"doctype": "Item", "item_code": lab_test_code}):
		frappe.throw(_("Lab Test Item {0} already exist").format(lab_test_code))
	else:
		rename_doc("Item", doc.name, lab_test_code, ignore_permissions=True)
		frappe.db.set_value("Lab Test Template", doc.name, "lab_test_code", lab_test_code)
		frappe.db.set_value("Lab Test Template", doc.name, "lab_test_name", lab_test_code)
		rename_doc("Lab Test Template", doc.name, lab_test_code, ignore_permissions=True)
	return lab_test_code
