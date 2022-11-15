# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt
from frappe.model.document import Document


class VehiclePricingComponent(Document):
	def validate(self):
		self.validate_component_type()
		self.validate_duplicate_component()
		self.validate_default_price_list()
		self.validate_price_list_mandatory()
		self.validate_duplicate_territory()

	def validate_component_type(self):
		if self.component_type != 'Booking':
			self.booking_component_type = ""
		if self.component_type != 'Registration':
			self.registration_component_type = ""

	def validate_duplicate_component(self):
		type_fieldnames = ['booking_component_type', 'registration_component_type']
		for f in type_fieldnames:
			if self.get(f):
				label = self.meta.get_label(f)

				filters = {f: self.get(f)}
				if not self.is_new():
					filters['name'] = ['!=', self.name]

				existing = frappe.db.exists("Vehicle Pricing Component", filters)
				if existing:
					frappe.throw(_("Component with {0} {1} already exists: {2}")
						.format(label, frappe.bold(self.get(f)), existing))

	def validate_default_price_list(self):
		default_price_lists = [d for d in self.price_lists if cint(d.get('is_default'))]
		if len(default_price_lists) > 1:
			frappe.throw(_("There can only be one default Price List"))

	def validate_price_list_mandatory(self):
		for d in self.price_lists:
			if not d.selling_price_list and not d.buying_price_list and not d.agent_price_list\
					and not flt(d.selling_price) and not flt(d.buying_price) and not flt(d.agent_price):
				frappe.throw(_("Row #{0}: Please set either Selling Price or Buying Price or Agent Price or remove the row")
					.format(d.idx))

	def validate_duplicate_territory(self):
		territories_visited = set()
		for d in self.price_lists:
			territory = cstr(d.territory)
			if territory in territories_visited:
				if territory:
					frappe.throw(_("Row #{0}: Price List for Territory {1} is already defined")
						.format(d.idx, territory))
				else:
					frappe.throw(_("Row #{0}: Price List without Territory is already defined")
						.format(d.idx))

			territories_visited.add(territory)

	def get_default_price_list_row(self):
		default_price_lists = [d for d in self.price_lists if cint(d.get('is_default'))]
		return default_price_lists[0] if default_price_lists else None
