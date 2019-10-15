# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.support.doctype.service_level.test_service_level import create_service_level_for_sla

class TestServiceLevelAgreement(unittest.TestCase):

	def test_service_level_agreement(self):
		frappe.db.set_value("Support Settings", None, "track_service_level_agreement", 1)

		create_service_level_for_sla()

		# Default Service Level Agreement
		create_default_service_level_agreement = create_service_level_agreement(default_service_level_agreement=1,
			service_level="__Test Service Level", holiday_list="__Test Holiday List", employee_group="_Test Employee Group",
			entity_type=None, entity=None, response_time=4, resolution_time=6)
		get_default_service_level_agreement = get_service_level_agreement(default_service_level_agreement=1)

		self.assertEqual(create_default_service_level_agreement.name, get_default_service_level_agreement.name)
		self.assertEqual(create_default_service_level_agreement.entity_type, get_default_service_level_agreement.entity_type)
		self.assertEqual(create_default_service_level_agreement.entity, get_default_service_level_agreement.entity)
		self.assertEqual(create_default_service_level_agreement.default_service_level_agreement, get_default_service_level_agreement.default_service_level_agreement)

		# Service Level Agreement for Customer
		customer = create_customer()
		create_customer_service_level_agreement = create_service_level_agreement(default_service_level_agreement=0,
			service_level="_Test Service Level", holiday_list="__Test Holiday List", employee_group="_Test Employee Group",
			entity_type="Customer", entity=customer, response_time=2, resolution_time=3)
		get_customer_service_level_agreement = get_service_level_agreement(entity_type="Customer", entity=customer)

		self.assertEqual(create_customer_service_level_agreement.name, get_customer_service_level_agreement.name)
		self.assertEqual(create_customer_service_level_agreement.entity_type, get_customer_service_level_agreement.entity_type)
		self.assertEqual(create_customer_service_level_agreement.entity, get_customer_service_level_agreement.entity)
		self.assertEqual(create_customer_service_level_agreement.default_service_level_agreement, get_customer_service_level_agreement.default_service_level_agreement)

		# Service Level Agreement for Customer Group
		customer_group = create_customer_group()
		create_customer_group_service_level_agreement = create_service_level_agreement(default_service_level_agreement=0,
			service_level="_Test Service Level", holiday_list="__Test Holiday List", employee_group="_Test Employee Group",
			entity_type="Customer Group", entity=customer_group, response_time=2, resolution_time=3)
		get_customer_group_service_level_agreement = get_service_level_agreement(entity_type="Customer Group", entity=customer_group)

		self.assertEqual(create_customer_group_service_level_agreement.name, get_customer_group_service_level_agreement.name)
		self.assertEqual(create_customer_group_service_level_agreement.entity_type, get_customer_group_service_level_agreement.entity_type)
		self.assertEqual(create_customer_group_service_level_agreement.entity, get_customer_group_service_level_agreement.entity)
		self.assertEqual(create_customer_group_service_level_agreement.default_service_level_agreement, get_customer_group_service_level_agreement.default_service_level_agreement)

		# Service Level Agreement for Territory
		territory = create_territory()
		create_territory_service_level_agreement = create_service_level_agreement(default_service_level_agreement=0,
			service_level="_Test Service Level", holiday_list="__Test Holiday List", employee_group="_Test Employee Group",
			entity_type="Territory", entity=territory, response_time=2, resolution_time=3)
		get_territory_service_level_agreement = get_service_level_agreement(entity_type="Territory", entity=territory)

		self.assertEqual(create_territory_service_level_agreement.name, get_territory_service_level_agreement.name)
		self.assertEqual(create_territory_service_level_agreement.entity_type, get_territory_service_level_agreement.entity_type)
		self.assertEqual(create_territory_service_level_agreement.entity, get_territory_service_level_agreement.entity)
		self.assertEqual(create_territory_service_level_agreement.default_service_level_agreement, get_territory_service_level_agreement.default_service_level_agreement)


def get_service_level_agreement(default_service_level_agreement=None, entity_type=None, entity=None):
	if default_service_level_agreement:
		filters = {"default_service_level_agreement": default_service_level_agreement}
	else:
		filters = {"entity_type": entity_type, "entity": entity}

	service_level_agreement = frappe.get_doc("Service Level Agreement", filters)
	return service_level_agreement

def create_service_level_agreement(default_service_level_agreement, service_level, holiday_list, employee_group,
	response_time, entity_type, entity, resolution_time):

	service_level_agreement = frappe.get_doc({
		"doctype": "Service Level Agreement",
		"enable": 1,
		"default_service_level_agreement": default_service_level_agreement,
		"service_level": service_level,
		"holiday_list": holiday_list,
		"employee_group": employee_group,
		"entity_type": entity_type,
		"entity": entity,
		"start_date": frappe.utils.getdate(),
		"end_date": frappe.utils.add_to_date(frappe.utils.getdate(), days=100),
		"priorities": [
			{
				"priority": "Low",
				"response_time": response_time,
				"response_time_period": "Hour",
				"resolution_time": resolution_time,
				"resolution_time_period": "Hour",
			},
			{
				"priority": "Medium",
				"response_time": response_time,
				"default_priority": 1,
				"response_time_period": "Hour",
				"resolution_time": resolution_time,
				"resolution_time_period": "Hour",
			},
			{
				"priority": "High",
				"response_time": response_time,
				"response_time_period": "Hour",
				"resolution_time": resolution_time,
				"resolution_time_period": "Hour",
			}
		],
		"support_and_resolution": [
			{
				"workday": "Monday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Tuesday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Wednesday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Thursday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Friday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Saturday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Sunday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			}
		]
	})

	filters = {
		"default_service_level_agreement": service_level_agreement.default_service_level_agreement,
		"service_level": service_level_agreement.service_level
	}

	if not default_service_level_agreement:
		filters.update({
			"entity_type": entity_type,
			"entity": entity
		})

	service_level_agreement_exists = frappe.db.exists("Service Level Agreement", filters)

	if not service_level_agreement_exists:
		service_level_agreement.insert(ignore_permissions=True)
		return service_level_agreement
	else:
		return frappe.get_doc("Service Level Agreement", service_level_agreement_exists)

def create_customer():
	customer = frappe.get_doc({
		"doctype": "Customer",
		"customer_name": "_Test Customer",
		"customer_group": "Commercial",
		"customer_type": "Individual",
		"territory": "Rest Of The World"
	})
	if not frappe.db.exists("Customer", "_Test Customer"):
		customer.insert(ignore_permissions=True)
		return customer.name
	else:
		return frappe.db.exists("Customer", "_Test Customer")

def create_customer_group():
	customer_group = frappe.get_doc({
		"doctype": "Customer Group",
		"customer_group_name": "_Test SLA Customer Group"
	})

	if not frappe.db.exists("Customer Group", {"customer_group_name": "_Test SLA Customer Group"}):
		customer_group.insert()
		return customer_group.name
	else:
		return frappe.db.exists("Customer Group", {"customer_group_name": "_Test SLA Customer Group"})

def create_territory():
	territory = frappe.get_doc({
		"doctype": "Territory",
		"territory_name": "_Test SLA Territory",
	})

	if not frappe.db.exists("Territory", {"territory_name": "_Test SLA Territory"}):
		territory.insert()
		return territory.name
	else:
		return frappe.db.exists("Territory", {"territory_name": "_Test SLA Territory"})

def create_service_level_agreements_for_issues():
	create_service_level_for_sla()

	create_service_level_agreement(default_service_level_agreement=1,
		service_level="__Test Service Level", holiday_list="__Test Holiday List", employee_group="_Test Employee Group",
		entity_type=None, entity=None, response_time=4, resolution_time=6)

	create_customer()
	create_service_level_agreement(default_service_level_agreement=0,
		service_level="_Test Service Level", holiday_list="__Test Holiday List", employee_group="_Test Employee Group",
		entity_type="Customer", entity="_Test Customer", response_time=2, resolution_time=3)

	create_customer_group()
	create_service_level_agreement(default_service_level_agreement=0,
		service_level="_Test Service Level", holiday_list="__Test Holiday List", employee_group="_Test Employee Group",
		entity_type="Customer Group", entity="_Test SLA Customer Group", response_time=2, resolution_time=3)

	create_territory()
	create_service_level_agreement(default_service_level_agreement=0,
		service_level="_Test Service Level", holiday_list="__Test Holiday List", employee_group="_Test Employee Group",
		entity_type="Territory", entity="_Test SLA Territory", response_time=2, resolution_time=3)
