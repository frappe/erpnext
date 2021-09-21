# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint
from erpnext.vehicles.vehicle_additional_service import VehicleAdditionalServiceController
from erpnext.vehicles.vehicle_pricing import calculate_total_price, validate_duplicate_components,\
	validate_component_type, validate_disabled_component


class VehicleRegistrationOrder(VehicleAdditionalServiceController):
	def get_feed(self):
		return _("From {0} | {1}").format(self.get("customer_name") or self.get('customer'),
			self.get("item_name") or self.get("item_code"))

	def validate(self):
		super(VehicleRegistrationOrder, self).validate()
		self.validate_vehicle_unregistered()
		self.validate_choice_number()

		self.validate_pricing_components()
		self.calculate_totals()
		self.reset_outstanding_amount()

		self.validate_agent_mandatory()
		self.set_title()

	def validate_vehicle_unregistered(self):
		if self.vehicle:
			license_plate = frappe.db.get_value("Vehicle", self.vehicle, "license_plate")
			if license_plate:
				frappe.throw(_("{0} is already registered: {1}")
					.format(frappe.get_desk_link("Vehicle", self.vehicle), license_plate))

	def validate_choice_number(self):
		if not cint(self.choice_number_required):
			self.choice_number_details = ""

	def validate_pricing_components(self):
		validate_disabled_component(self.get('customer_charges'))
		validate_disabled_component(self.get('authority_charges'))

		validate_duplicate_components(self.get('customer_charges'))
		validate_duplicate_components(self.get('authority_charges'))

		validate_component_type("Registration", self.get('customer_charges'))
		validate_component_type("Registration", self.get('authority_charges'))

	def validate_agent_mandatory(self):
		if flt(self.agent_commission) and not self.agent:
			frappe.throw(_("Registration Agent is mandatory for Registration Agent Commission"))

	def calculate_totals(self):
		calculate_total_price(self, 'customer_charges', 'customer_total')
		calculate_total_price(self, 'authority_charges', 'authority_total')

		self.round_floats_in(self, ['agent_commission'])

		self.margin_amount = flt(self.customer_total - self.authority_total - self.agent_commission,
			self.precision('margin_amount'))

	def reset_outstanding_amount(self):
		if self.docstatus == 0:
			self.customer_outstanding = flt(self.customer_total)
			self.agent_outstanding = 0

	def set_title(self):
		self.title = "{0}{1}".format(self.customer_name or self.customer, ' ({0})'.format(self.get('received_by')) if self.get('received_by') else '')
