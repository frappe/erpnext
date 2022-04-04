# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class VehicleWorkshop(Document):
	pass


@frappe.whitelist()
def get_vehicle_workshop_details(vehicle_workshop):
	doc = frappe.get_cached_doc("Vehicle Workshop", vehicle_workshop)
	out = frappe._dict()
	out.service_manager = doc.service_manager
	return out
