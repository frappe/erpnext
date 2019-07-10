# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate

class ServiceLevelAgreement(Document):

	def validate(self):
		if not frappe.db.get_single_value("Support Settings", "track_service_level_agreement"):
			frappe.throw(_("Service Level Agreement tracking is not enabled."))

		if self.default_service_level_agreement:
			if frappe.db.exists("Service Level Agreement", {"default_service_level_agreement": "1", "name": ["!=", self.name]}):
				frappe.throw(_("A Default Service Level Agreement already exists."))
		else:
			if self.start_date and self.end_date:
				if getdate(self.start_date) >= getdate(self.end_date):
					frappe.throw(_("Start Date of Agreement can't be greater than or equal to End Date."))

				if getdate(self.end_date) < getdate(frappe.utils.getdate()):
					frappe.throw(_("End Date of Agreement can't be less than today."))

		if self.entity_type and self.entity:
			if frappe.db.exists("Service Level Agreement", {"entity_type": self.entity_type, "entity": self.entity, "name": ["!=", self.name]}):
				frappe.throw(_("Service Level Agreement with Entity Type {0} and Entity {1} already exists.").format(self.entity_type, self.entity))

	def get_service_level_agreement_priority(self, priority):
		priority = frappe.get_doc("Service Level Priority", {"priority": priority, "parent": self.name})

		return frappe._dict({
			"priority": priority.priority,
			"response_time": priority.response_time,
			"response_time_period": priority.response_time_period,
			"resolution_time": priority.resolution_time,
			"resolution_time_period": priority.resolution_time_period
		})

def check_agreement_status():
	service_level_agreements = frappe.get_list("Service Level Agreement", filters=[
		{"active": 1},
		{"default_service_level_agreement": 0}
	], fields=["name"])

	for service_level_agreement in service_level_agreements:
		doc = frappe.get_doc("Service Level Agreement", service_level_agreement.name)
		if doc.end_date and getdate(doc.end_date) < getdate(frappe.utils.getdate()):
			frappe.db.set_value("Service Level Agreement", service_level_agreement.name, "active", 0)

def get_active_service_level_agreement_for(priority, customer=None, service_level_agreement=None):
	if not frappe.db.get_single_value("Support Settings", "track_service_level_agreement"):
		return

	filters = [
		["Service Level Agreement", "active", "=", 1],
		["Service Level Agreement", "enable", "=", 1]
	]

	if priority:
		filters.append(["Service Level Priority", "priority", "=", priority])

	or_filters = [
		["Service Level Agreement", "entity", "in", [customer, get_customer_group(customer), get_customer_territory(customer)]]
	]
	if service_level_agreement:
		or_filters = [
			["Service Level Agreement", "name", "=", service_level_agreement],
		]

	or_filters.append(["Service Level Agreement", "default_service_level_agreement", "=", 1])

	agreement = frappe.get_list("Service Level Agreement", filters=filters, or_filters=or_filters,
		fields=["name", "default_priority"])

	return agreement[0] if agreement else None

def get_customer_group(customer):
	if customer:
		return frappe.db.get_value("Customer", customer, "customer_group")

def get_customer_territory(customer):
	if customer:
		return frappe.db.get_value("Customer", customer, "territory")

@frappe.whitelist()
def get_service_level_agreement_filters(name, customer=None):
	if not frappe.db.get_single_value("Support Settings", "track_service_level_agreement"):
		return

	filters = [
		["Service Level Agreement", "active", "=", 1],
		["Service Level Agreement", "enable", "=", 1]
	]

	if not customer:
		or_filters = [
			["Service Level Agreement", "default_service_level_agreement", "=", 1]
		]
	else:
		# Include SLA with No Entity and Entity Type
		or_filters = [
			["Service Level Agreement", "entity", "in", [customer, get_customer_group(customer), get_customer_territory(customer), ""]],
			["Service Level Agreement", "default_service_level_agreement", "=", 1]
		]

	return {
		"priority": [priority.priority for priority in frappe.get_list("Service Level Priority", filters={"parent": name}, fields=["priority"])],
		"service_level_agreements": [d.name for d in frappe.get_list("Service Level Agreement", filters=filters, or_filters=or_filters)]
	}