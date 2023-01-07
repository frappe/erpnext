# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cstr
from erpnext.controllers.status_updater import StatusUpdater


class HandlingUnit(StatusUpdater):
	def onload(self):
		self.set_onload('cant_change_fields', self.get_cant_change_fields())

	def validate(self):
		self.validate_cant_change()
		self.set_status()

	def set_status(self, update=False, status=None, update_modified=True):
		previous_status = self.status

		packing_slip = self.get_packing_slip_details()
		self.package_type = packing_slip.package_type if packing_slip else self.package_type
		self.company = packing_slip.company if packing_slip else self.company
		self.warehouse = packing_slip.to_warehouse
		self.customer = packing_slip.customer
		self.customer_name = packing_slip.customer

		if not packing_slip:
			self.status = "Inactive"
		else:
			stock_qty = self.get_stock_qty()
			if stock_qty:
				self.status = "In Stock"
			else:
				self.status = "Delivered"

		self.add_status_comment(previous_status)

		if update:
			self.db_set({
				"status": self.status,
				"package_type": self.package_type,
				"company": self.company,
				"warehouse": self.warehouse,
				"customer": self.customer,
				"customer_name": self.customer_name,
			}, None, update_modified=update_modified)

	def get_packing_slip_details(self):
		if self.is_new():
			return frappe._dict()

		packing_slip = frappe.db.get_value("Packing Slip", {"handling_unit": self.name, "docstatus": 1},
			fieldname=["name", "package_type", "to_warehouse", "customer", "customer_name", "company"], as_dict=1)

		return packing_slip or frappe._dict()

	def get_stock_qty(self):
		if self.is_new():
			return 0

		stock_qty = frappe.db.sql("""
			select sum(actual_qty)
			from `tabStock Ledger Entry`
			where handling_unit = %s
		""", self.name)

		return flt(stock_qty[0][0]) if stock_qty else 0

	def validate_cant_change(self):
		if self.is_new():
			return

		fields = self.get_cant_change_fields()
		cant_change_fields = [f for f, cant_change in fields.items() if cant_change]

		if cant_change_fields:
			previous_values = frappe.db.get_value(self.doctype, self.name, cant_change_fields, as_dict=1)
			for f, old_value in previous_values.items():
				if cstr(self.get(f)) != cstr(old_value):
					label = self.meta.get_label(f)
					frappe.throw(_("Cannot change {0} because Handling Unit is already packed")
						.format(frappe.bold(label)))

	def get_cant_change_fields(self):
		is_packed = self.is_packed()
		return frappe._dict({
			'package_type': is_packed,
			'company': is_packed,
		})

	def is_packed(self):
		if not hasattr(self, '_is_packed'):
			self._is_packed = frappe.db.get_value("Packing Slip",
				{"handling_unit": self.name, "docstatus": 1})

		return self._is_packed
