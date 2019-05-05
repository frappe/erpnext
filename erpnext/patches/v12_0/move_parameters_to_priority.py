# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	priorities = ["Low", "Medium", "High"]

	service_levels = frappe.get_list("Service Level",
		fields=["name", "priority", "response_time", "response_time_period", "resolution_time", "resolution_time_period"])
	for service_level in service_levels:
		for idx, value in enumerate(priorities):
			doc = frappe.get_doc({
				"doctype": "Service Level Priority",
				"parent": service_level.name,
				"parenttype": "Service Level",
				"priority": value,
				"idx": idx,
				"response_time": service_level.response_time,
				"response_time_period": service_level.response_time_period,
				"resolution_time": service_level.resolution_time,
				"resolution_time_period": service_level.resolution_time_period,
			}).insert(ignore_permissions=True)

	service_level_agreements = frappe.get_list("Service Level Agreement",
		fields=["name", "priority", "response_time", "response_time_period", "resolution_time", "resolution_time_period"])
	for service_level_agreement in service_level_agreements:
		for idx, value in enumerate(priorities):
			doc = frappe.get_doc({
				"doctype": "Service Level Priority",
				"parent": service_level_agreement.name,
				"parenttype": "Service Level Agreement",
				"priority": value,
				"idx": idx,
				"response_time": service_level_agreement.response_time,
				"response_time_period": service_level_agreement.response_time_period,
				"resolution_time": service_level_agreement.resolution_time,
				"resolution_time_period": service_level_agreement.resolution_time_period,
			}).insert(ignore_permissions=True)