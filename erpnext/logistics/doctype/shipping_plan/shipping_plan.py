# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cint, flt
from collections import defaultdict
from erpnext.logistics.controller.fedex_controller import FedExController

class ShippingPlan(Document):
	def __init__(self, *args, **kwargs):
		super(ShippingPlan, self).__init__(*args, **kwargs)
		self.controller = FedExController(args=self)

	def validate(self):
		self.controller.validate()
		self.validate_delivery_note()
		self.validate_items_mandatory()
		self.validate_for_existing_shipping_plan()
		self.validate_postal_code()
		self.validate_for_package_count()
		self.validate_package_details()
		self.set_net_weight_of_packages()

	def validate_delivery_note(self):
		"""
			validate if delivery note has status as draft
		"""
		if cint(frappe.db.get_value("Delivery Note", self.delivery_note, "docstatus")) != 0:
			frappe.throw(_("Delivery Note {0} must not be submitted").format(self.delivery_note))

	def validate_items_mandatory(self):
		if not len(self.items):
			frappe.msgprint(_("No Items for Shipping Plan"), raise_exception=1)

	def validate_for_existing_shipping_plan(self):
		"""
			check if Shipping Plan is already created against self.delivery_note
		"""
		shipping_plan = frappe.db.get_value("Shipping Plan", {"name":["not in", [self.name]],\
			"delivery_note":self.delivery_note, "docstatus":["in", ["0"]]}, "name")
		if shipping_plan:
			frappe.throw(_("Shipping Plan {0} already created against delivery note {1}.".\
				format(shipping_plan, self.delivery_note)))

	def validate_postal_code(self):
		"""
			validate Shipping Address with Postal Code.
		"""
		address = frappe.db.get_value("Address", {"name":self.get("shipping_address_name")}, "*", as_dict=True)
		if not frappe.db.get_value("Postal Code", {"postal_code":address.get("pincode"), \
			"country_name":address.get("country")}, "name"):
			frappe.throw(_("FedEx shipment delivery is not allowed at Recipient postal code {0}".format(address.get("pincode"))))

	def validate_for_package_count(self):
		if self.no_of_packages != len(self.packages):
			frappe.throw(_("No of Packages must be equal to Package Details table"))

	def validate_package_details(self):
		"""
			validate Item Distribution with Packages
		"""
		item_packing_dict, item_package_ids, package_wt, no_of_pieces, total_qty = self.get_item_packing_details()
		package_ids = []
		for row in self.packages:
			if row.package_no not in item_package_ids:
				frappe.throw(_("Package {0} not linked to any item".format(row.package_no)))
			package_ids.append(row.package_no)

		packed_items = item_packing_dict.keys()
		for row in self.items:
			if row.item_code not in packed_items:
				frappe.throw(_("Item {0} in row {1} not found in Item Packing Details \
					table".format(row.item_code, row.idx)))
			if row.qty != item_packing_dict.get(row.item_code, 0):
				frappe.throw(_("Item {0} quantity {1} is not equal to quantity {2} mentioned in\
					Package Item Details table.".format(row.item_code, flt(row.qty), item_packing_dict.get(row.item_code, 0))))

	def update_package_details(self):
		"""
			Update Item & Package Details
		"""
		item_packing_dict, item_package_ids, package_wt, no_of_pieces, total_qty = get_item_packing_dict(doc)
		self.total_handling_units = cint(total_qty)
		for row in self.items:
			row.no_of_pieces = len(no_of_pieces.get(row.item_code))

		for row in self.packages:
			row.package_weight = package_wt.get(row.package_no, 0)
			row.uom = self.gross_weight_uom

	def set_net_weight_of_packages(self):
		"""
			Set net_weight of items from Item to Package Items table
		"""
		item_wt = {row.item_code:row.net_weight for row in self.items}
		for row in self.package_items:
			row.net_weight = item_wt.get(row.item_code, 0)

	def get_item_packing_details(self):
		"""
			Returns
			* item_packing_dict: Dict of Item Code - Qty
			* item_package_ids: Set of Package No's
			* package_wt: Dict of Package No - Package Weight
			* no_of_pieces: Dict of Item Code - set(Package No's)
			* total_qty: Total Item Qty
		"""
		item_packing_dict = package_wt = defaultdict(float)
		no_of_pieces = defaultdict(set)
		item_package_ids = set()
		total_qty = 0
		for row in self.package_items:
			item_packing_dict[row.item_code] += row.qty
			package_wt[row.package_no] += flt(row.qty) * flt(row.net_weight)
			no_of_pieces[row.item_code].add(row.package_no)
			item_package_ids.add(row.package_no)
			total_qty += row.qty
		return item_packing_dict, item_package_ids, package_wt, no_of_pieces, total_qty