# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class ServiceUnit(Document):
	def validate(self):
		for child in self.assigned_users:
			if child.user :
				validate_for_enabled_user(child.user)
				#validate_duplicate_user(child.user, self.name, child.name)

	def on_update(self):
		if self.zones:
			service_units_to_zone(self)
		for child in self.assigned_users:
			if child.user :
				frappe.permissions.add_user_permission("Service Unit", self.name, child.user)

def validate_for_enabled_user(user):
	enabled = frappe.db.get_value("User", user, "enabled")
	if enabled is None:
		frappe.throw(_("User {0} does not exist").format(user))
	if enabled == 0:
		frappe.throw(_("User {0} is disabled").format(user))

def validate_duplicate_user(user, parent):
	users = frappe.db.sql_list("""select name from `tabUser List` where
		user=%s and parent=%s""", (user, parent))
	if users:
		frappe.throw(_("Service Unit {0} is already assigned to User {1}").format(parent, user), frappe.DuplicateEntryError)

def service_units_to_zone(self):
	for z in self.zones:
		zone = frappe.get_doc("Zone", z.zone)
		for service_type in self.service_type_list:
			for units in zone.service_units:
				if(units.service_unit == self.name):
					continue
				elif units.type == service_type.service_type :
					#a service type appeare only once in a zone
					frappe.throw(_("{0} for zone {1} is managed by service unit {2}").format(service_type.service_type, zone.name, units.service_unit))

			add_unit_to_zone(zone, self.name, service_type.service_type)

def add_unit_to_zone(zone, service_unit, service_type):
	unit = zone.append("service_units")
	unit.service_unit = service_unit
	unit.type = service_type
	zone.save(ignore_permissions=True)
