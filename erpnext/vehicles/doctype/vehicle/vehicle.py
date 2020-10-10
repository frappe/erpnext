# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, nowdate, cstr
from frappe.model.document import Document
from frappe.model.naming import make_autoname

class Vehicle(Document):
	def autoname(self):
		if self.flags.from_serial_no:
			self.name = self.flags.from_serial_no
		else:
			item = frappe.get_cached_doc("Item", self.item_code)
			serial_no_series = item.serial_no_series
			if serial_no_series:
				self.name = make_autoname(serial_no_series, "Serial No", item)

	def onload(self):
		self.copy_image_from_item()

	def on_update(self):
		self.update_vehicle_serial_no()

	def validate(self):
		self.validate_item()
		self.update_reference_from_serial_no()
		self.set_status()

	def on_trash(self):
		self.delete_serial_no_on_trash()

	def copy_image_from_item(self):
		if not self.image:
			self.image = frappe.get_cached_value('Item', self.item_code, 'image')

	def update_vehicle_serial_no(self):
		if self.flags.from_serial_no:
			serial_no_doc = frappe.get_cached_doc("Serial No", self.flags.from_serial_no)
			serial_no_doc.db_set('vehicle', self.name)
		else:
			if not frappe.db.exists("Serial No", self.name):
				serial_no_doc = frappe.new_doc("Serial No")
				serial_no_doc.flags.from_vehicle = self.name
				serial_no_doc.serial_no = self.name
				serial_no_doc.vehicle = self.name
				serial_no_doc.item_code = self.item_code
				serial_no_doc.insert()

	def validate_item(self):
		item = frappe.get_cached_doc("Item", self.item_code)
		if not item.is_vehicle:
			frappe.throw(_("Item {0} is not setup as a Vehicle Item").format(self.item_code))

		self.item_group = item.item_group
		self.item_name = item.item_name
		self.brand = item.brand
		self.warranty_period = item.warranty_period

	def update_reference_from_serial_no(self, serial_no_doc=None):
		if not serial_no_doc:
			serial_no_doc = self.get_serial_no_doc()

		if not serial_no_doc:
			return

		if cstr(self.get('sales_order')) != cstr(self.db_get('sales_order')):
			serial_no_doc.sales_order = self.sales_order
			serial_no_doc.flags.from_vehicle = self.name
			serial_no_doc.save()

		fields = [
			'company',
			'warehouse', 'sales_order',
			'customer', 'customer_name',
			'supplier', 'supplier_name',
			'purchase_document_type', 'purchase_document_no', 'purchase_date', 'purchase_time', 'purchase_rate',
			'delivery_document_type', 'delivery_document_no', 'delivery_date', 'delivery_time', 'sales_invoice',
			'warranty_expiry_date', 'amc_expiry_date'
		]

		for f in fields:
			self.set(f, serial_no_doc.get(f))

	def delete_serial_no_on_trash(self):
		if frappe.db.exists("Serial No", self.name):
			frappe.delete_doc("Serial No", self.name)

	def get_serial_no_doc(self):
		serial_no_doc = None
		if self.flags.from_serial_no:
			serial_no_doc = frappe.get_cached_doc("Serial No", self.flags.from_serial_no)
		else:
			serial_no_name = frappe.db.get_value("Serial No", {"vehicle": self.name}, "name")
			if serial_no_name:
				serial_no_doc = frappe.get_doc("Serial No", serial_no_name)

		return serial_no_doc

	def set_status(self):
		if self.delivery_document_type:
			self.status = "Delivered"
		elif self.warranty_expiry_date and getdate(self.warranty_expiry_date) <= getdate(nowdate()):
			self.status = "Expired"
		elif not self.warehouse:
			self.status = "Inactive"
		else:
			self.status = "Active"
