# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, get_weekdays, get_link_to_form

class ServiceLevelAgreement(Document):

	def validate(self):
		self.validate_doc()
		self.check_priorities()
		self.check_support_and_resolution()

	def check_priorities(self):
		default_priority = []
		priorities = []

		for priority in self.priorities:
			# Check if response and resolution time is set for every priority
			if not priority.response_time or not priority.resolution_time:
				frappe.throw(_("Set Response Time and Resolution Time for Priority {0} in row {1}.").format(priority.priority, priority.idx))

			priorities.append(priority.priority)

			if priority.default_priority:
				default_priority.append(priority.default_priority)

			response = priority.response_time
			resolution = priority.resolution_time

			if response > resolution:
				frappe.throw(_("Response Time for {0} priority in row {1} can't be greater than Resolution Time.").format(priority.priority, priority.idx))

		# Check if repeated priority
		if not len(set(priorities)) == len(priorities):
			repeated_priority = get_repeated(priorities)
			frappe.throw(_("Priority {0} has been repeated.").format(repeated_priority))

		# Check if repeated default priority
		if not len(set(default_priority)) == len(default_priority):
			frappe.throw(_("Select only one Priority as Default."))

		# set default priority from priorities
		try:
			self.default_priority = next(d.priority for d in self.priorities if d.default_priority)
		except Exception:
			frappe.throw(_("Select a Default Priority."))

	def check_support_and_resolution(self):
		week = get_weekdays()
		support_days = []

		for support_and_resolution in self.support_and_resolution:
			# Check if start and end time is set for every support day
			if not (support_and_resolution.start_time or support_and_resolution.end_time):
				frappe.throw(_("Set Start Time and End Time for  \
					Support Day {0} at index {1}.".format(support_and_resolution.workday, support_and_resolution.idx)))

			support_days.append(support_and_resolution.workday)
			support_and_resolution.idx = week.index(support_and_resolution.workday) + 1

			if support_and_resolution.start_time >= support_and_resolution.end_time:
				frappe.throw(_("Start Time can't be greater than or equal to End Time \
					for {0}.".format(support_and_resolution.workday)))

		# Check for repeated workday
		if not len(set(support_days)) == len(support_days):
			repeated_days = get_repeated(support_days)
			frappe.throw(_("Workday {0} has been repeated.").format(repeated_days))

	def validate_doc(self):
		if not frappe.db.get_single_value("Support Settings", "track_service_level_agreement") and self.enable:
			frappe.throw(_("{0} is not enabled in {1}").format(frappe.bold("Track Service Level Agreement"),
				get_link_to_form("Support Settings", "Support Settings")))

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
			"resolution_time": priority.resolution_time
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

def get_repeated(values):
	unique_list = []
	diff = []
	for value in values:
		if value not in unique_list:
			unique_list.append(str(value))
		else:
			if value not in diff:
				diff.append(str(value))
	return " ".join(diff)
