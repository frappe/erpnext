# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import datetime
import unittest

import frappe
from frappe.utils import flt

from erpnext.support.doctype.issue_priority.test_issue_priority import make_priorities
from erpnext.support.doctype.service_level_agreement.service_level_agreement import (
	get_service_level_agreement_fields,
)


class TestServiceLevelAgreement(unittest.TestCase):
	def setUp(self):
		self.create_company()
		frappe.db.set_value("Support Settings", None, "track_service_level_agreement", 1)
		lead = frappe.qb.DocType("Lead")
		frappe.qb.from_(lead).delete().where(lead.company == self.company).run()

	def create_company(self):
		name = "_Test Support SLA"
		company = None
		if frappe.db.exists("Company", name):
			company = frappe.get_doc("Company", name)
		else:
			company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": name,
					"country": "India",
					"default_currency": "INR",
					"create_chart_of_accounts_based_on": "Standard Template",
					"chart_of_accounts": "Standard",
				}
			)
			company = company.save()

		self.company = company.name

	def test_service_level_agreement(self):
		# Default Service Level Agreement
		create_default_service_level_agreement = create_service_level_agreement(
			default_service_level_agreement=1,
			holiday_list="__Test Holiday List",
			entity_type=None,
			entity=None,
			response_time=14400,
			resolution_time=21600,
		)

		get_default_service_level_agreement = get_service_level_agreement(
			default_service_level_agreement=1
		)

		self.assertEqual(
			create_default_service_level_agreement.name, get_default_service_level_agreement.name
		)
		self.assertEqual(
			create_default_service_level_agreement.entity_type,
			get_default_service_level_agreement.entity_type,
		)
		self.assertEqual(
			create_default_service_level_agreement.entity, get_default_service_level_agreement.entity
		)
		self.assertEqual(
			create_default_service_level_agreement.default_service_level_agreement,
			get_default_service_level_agreement.default_service_level_agreement,
		)

		# Service Level Agreement for Customer
		customer = create_customer()
		create_customer_service_level_agreement = create_service_level_agreement(
			default_service_level_agreement=0,
			holiday_list="__Test Holiday List",
			entity_type="Customer",
			entity=customer,
			response_time=7200,
			resolution_time=10800,
		)
		get_customer_service_level_agreement = get_service_level_agreement(
			entity_type="Customer", entity=customer
		)

		self.assertEqual(
			create_customer_service_level_agreement.name, get_customer_service_level_agreement.name
		)
		self.assertEqual(
			create_customer_service_level_agreement.entity_type,
			get_customer_service_level_agreement.entity_type,
		)
		self.assertEqual(
			create_customer_service_level_agreement.entity, get_customer_service_level_agreement.entity
		)
		self.assertEqual(
			create_customer_service_level_agreement.default_service_level_agreement,
			get_customer_service_level_agreement.default_service_level_agreement,
		)

		# Service Level Agreement for Customer Group
		customer_group = create_customer_group()
		create_customer_group_service_level_agreement = create_service_level_agreement(
			default_service_level_agreement=0,
			holiday_list="__Test Holiday List",
			entity_type="Customer Group",
			entity=customer_group,
			response_time=7200,
			resolution_time=10800,
		)
		get_customer_group_service_level_agreement = get_service_level_agreement(
			entity_type="Customer Group", entity=customer_group
		)

		self.assertEqual(
			create_customer_group_service_level_agreement.name,
			get_customer_group_service_level_agreement.name,
		)
		self.assertEqual(
			create_customer_group_service_level_agreement.entity_type,
			get_customer_group_service_level_agreement.entity_type,
		)
		self.assertEqual(
			create_customer_group_service_level_agreement.entity,
			get_customer_group_service_level_agreement.entity,
		)
		self.assertEqual(
			create_customer_group_service_level_agreement.default_service_level_agreement,
			get_customer_group_service_level_agreement.default_service_level_agreement,
		)

		# Service Level Agreement for Territory
		territory = create_territory()
		create_territory_service_level_agreement = create_service_level_agreement(
			default_service_level_agreement=0,
			holiday_list="__Test Holiday List",
			entity_type="Territory",
			entity=territory,
			response_time=7200,
			resolution_time=10800,
		)
		get_territory_service_level_agreement = get_service_level_agreement(
			entity_type="Territory", entity=territory
		)

		self.assertEqual(
			create_territory_service_level_agreement.name, get_territory_service_level_agreement.name
		)
		self.assertEqual(
			create_territory_service_level_agreement.entity_type,
			get_territory_service_level_agreement.entity_type,
		)
		self.assertEqual(
			create_territory_service_level_agreement.entity, get_territory_service_level_agreement.entity
		)
		self.assertEqual(
			create_territory_service_level_agreement.default_service_level_agreement,
			get_territory_service_level_agreement.default_service_level_agreement,
		)

	def test_custom_field_creation_for_sla_on_standard_dt(self):
		# Default Service Level Agreement
		doctype = "Lead"
		lead_sla = create_service_level_agreement(
			default_service_level_agreement=1,
			holiday_list="__Test Holiday List",
			entity_type=None,
			entity=None,
			response_time=14400,
			resolution_time=21600,
			doctype=doctype,
			sla_fulfilled_on=[{"status": "Converted"}],
		)

		# check default SLA for lead
		default_sla = get_service_level_agreement(default_service_level_agreement=1, doctype=doctype)
		self.assertEqual(lead_sla.name, default_sla.name)

		# check SLA custom fields created for leads
		sla_fields = get_service_level_agreement_fields()

		for field in sla_fields:
			self.assertTrue(
				frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": field.get("fieldname")})
			)

	def test_docfield_creation_for_sla_on_custom_dt(self):
		doctype = create_custom_doctype()
		sla = create_service_level_agreement(
			default_service_level_agreement=1,
			holiday_list="__Test Holiday List",
			entity_type=None,
			entity=None,
			response_time=14400,
			resolution_time=21600,
			doctype=doctype.name,
		)

		# check default SLA for custom dt
		default_sla = get_service_level_agreement(
			default_service_level_agreement=1, doctype=doctype.name
		)
		self.assertEqual(sla.name, default_sla.name)

		# check SLA docfields created
		sla_fields = get_service_level_agreement_fields()

		for field in sla_fields:
			self.assertTrue(
				frappe.db.exists("DocField", {"fieldname": field.get("fieldname"), "parent": doctype.name})
			)

	def test_sla_application(self):
		# Default Service Level Agreement
		doctype = "Lead"
		lead_sla = create_service_level_agreement(
			default_service_level_agreement=1,
			holiday_list="__Test Holiday List",
			entity_type=None,
			entity=None,
			response_time=14400,
			resolution_time=21600,
			doctype=doctype,
			sla_fulfilled_on=[{"status": "Converted"}],
		)

		# make lead with default SLA
		creation = datetime.datetime(2019, 3, 4, 12, 0)
		lead = make_lead(creation=creation, index=1, company=self.company)

		self.assertEqual(lead.service_level_agreement, lead_sla.name)
		self.assertEqual(lead.response_by, datetime.datetime(2019, 3, 4, 16, 0))
		self.assertEqual(lead.resolution_by, datetime.datetime(2019, 3, 4, 18, 0))

		frappe.flags.current_time = datetime.datetime(2019, 3, 4, 15, 0)
		lead.reload()
		lead.status = "Converted"
		lead.save()

		self.assertEqual(lead.agreement_status, "Fulfilled")

	def test_hold_time(self):
		doctype = "Lead"
		create_service_level_agreement(
			default_service_level_agreement=1,
			holiday_list="__Test Holiday List",
			entity_type=None,
			entity=None,
			response_time=14400,
			resolution_time=21600,
			doctype=doctype,
			sla_fulfilled_on=[{"status": "Converted"}],
			pause_sla_on=[{"status": "Replied"}],
		)

		creation = datetime.datetime(2020, 3, 4, 4, 0)
		lead = make_lead(creation, index=2, company=self.company)

		frappe.flags.current_time = datetime.datetime(2020, 3, 4, 4, 15)
		lead.reload()
		lead.status = "Replied"
		lead.save()

		lead.reload()
		self.assertEqual(lead.on_hold_since, frappe.flags.current_time)

		frappe.flags.current_time = datetime.datetime(2020, 3, 4, 5, 5)
		lead.reload()
		lead.status = "Converted"
		lead.save()

		lead.reload()
		self.assertEqual(flt(lead.total_hold_time, 2), 3000)
		self.assertEqual(lead.resolution_by, datetime.datetime(2020, 3, 4, 16, 50))

	def test_failed_sla_for_response_only(self):
		doctype = "Lead"
		create_service_level_agreement(
			default_service_level_agreement=1,
			holiday_list="__Test Holiday List",
			entity_type=None,
			entity=None,
			response_time=14400,
			doctype=doctype,
			sla_fulfilled_on=[{"status": "Replied"}],
			pause_sla_on=[],
			apply_sla_for_resolution=0,
		)

		creation = datetime.datetime(2019, 3, 4, 12, 0)
		lead = make_lead(creation=creation, index=1, company=self.company)
		self.assertEqual(lead.response_by, datetime.datetime(2019, 3, 4, 16, 0))

		# failed with response time only
		frappe.flags.current_time = datetime.datetime(2019, 3, 4, 16, 5)
		lead.reload()
		lead.status = "Replied"
		lead.save()

		lead.reload()
		self.assertEqual(lead.agreement_status, "Failed")

	def test_fulfilled_sla_for_response_only(self):
		doctype = "Lead"
		lead_sla = create_service_level_agreement(
			default_service_level_agreement=1,
			holiday_list="__Test Holiday List",
			entity_type=None,
			entity=None,
			response_time=14400,
			doctype=doctype,
			sla_fulfilled_on=[{"status": "Replied"}],
			apply_sla_for_resolution=0,
		)

		# fulfilled with response time only
		creation = datetime.datetime(2019, 3, 4, 12, 0)
		lead = make_lead(creation=creation, index=2, company=self.company)

		self.assertEqual(lead.service_level_agreement, lead_sla.name)
		self.assertEqual(lead.response_by, datetime.datetime(2019, 3, 4, 16, 0))

		frappe.flags.current_time = datetime.datetime(2019, 3, 4, 15, 30)
		lead.reload()
		lead.status = "Replied"
		lead.save()

		lead.reload()
		self.assertEqual(lead.agreement_status, "Fulfilled")

	def test_service_level_agreement_filters(self):
		doctype = "Lead"
		lead_sla = create_service_level_agreement(
			default_service_level_agreement=0,
			doctype=doctype,
			holiday_list="__Test Holiday List",
			entity_type=None,
			entity=None,
			condition='doc.source == "Test Source"',
			response_time=14400,
			sla_fulfilled_on=[{"status": "Replied"}],
			apply_sla_for_resolution=0,
		)
		creation = datetime.datetime(2019, 3, 4, 12, 0)
		lead = make_lead(creation=creation, index=4, company=self.company)
		applied_sla = frappe.db.get_value("Lead", lead.name, "service_level_agreement")
		self.assertFalse(applied_sla)

		source = frappe.get_doc(doctype="Lead Source", source_name="Test Source")
		source.insert(ignore_if_duplicate=True)
		lead.source = "Test Source"
		lead.save()
		applied_sla = frappe.db.get_value("Lead", lead.name, "service_level_agreement")
		self.assertEqual(applied_sla, lead_sla.name)

		# check if SLA is removed if condition fails
		lead.reload()
		lead.source = None
		lead.save()
		applied_sla = frappe.db.get_value("Lead", lead.name, "service_level_agreement")
		self.assertFalse(applied_sla)

	def tearDown(self):
		for d in frappe.get_all("Service Level Agreement"):
			frappe.delete_doc("Service Level Agreement", d.name, force=1)


def get_service_level_agreement(
	default_service_level_agreement=None, entity_type=None, entity=None, doctype="Issue"
):
	if default_service_level_agreement:
		filters = {
			"default_service_level_agreement": default_service_level_agreement,
			"document_type": doctype,
		}
	else:
		filters = {"entity_type": entity_type, "entity": entity}

	service_level_agreement = frappe.get_doc("Service Level Agreement", filters)
	return service_level_agreement


def create_service_level_agreement(
	default_service_level_agreement,
	holiday_list,
	response_time,
	entity_type,
	entity,
	resolution_time=0,
	doctype="Issue",
	condition="",
	sla_fulfilled_on=[],
	pause_sla_on=[],
	apply_sla_for_resolution=1,
	service_level=None,
	start_time="10:00:00",
	end_time="18:00:00",
):

	make_holiday_list()
	make_priorities()

	if not sla_fulfilled_on:
		sla_fulfilled_on = [{"status": "Resolved"}, {"status": "Closed"}]

	pause_sla_on = [{"status": "Replied"}] if doctype == "Issue" else pause_sla_on

	service_level_agreement = frappe._dict(
		{
			"doctype": "Service Level Agreement",
			"enabled": 1,
			"document_type": doctype,
			"service_level": service_level
			or "__Test {} SLA".format(entity_type if entity_type else "Default"),
			"default_service_level_agreement": default_service_level_agreement,
			"condition": condition,
			"default_priority": "Medium",
			"holiday_list": holiday_list,
			"entity_type": entity_type,
			"entity": entity,
			"start_date": frappe.utils.getdate(),
			"end_date": frappe.utils.add_to_date(frappe.utils.getdate(), days=100),
			"apply_sla_for_resolution": apply_sla_for_resolution,
			"priorities": [
				{
					"priority": "Low",
					"response_time": response_time,
					"resolution_time": resolution_time,
				},
				{
					"priority": "Medium",
					"response_time": response_time,
					"default_priority": 1,
					"resolution_time": resolution_time,
				},
				{
					"priority": "High",
					"response_time": response_time,
					"resolution_time": resolution_time,
				},
			],
			"sla_fulfilled_on": sla_fulfilled_on,
			"pause_sla_on": pause_sla_on,
			"support_and_resolution": [
				{
					"workday": "Monday",
					"start_time": start_time,
					"end_time": end_time,
				},
				{
					"workday": "Tuesday",
					"start_time": start_time,
					"end_time": end_time,
				},
				{
					"workday": "Wednesday",
					"start_time": start_time,
					"end_time": end_time,
				},
				{
					"workday": "Thursday",
					"start_time": start_time,
					"end_time": end_time,
				},
				{
					"workday": "Friday",
					"start_time": start_time,
					"end_time": end_time,
				},
			],
		}
	)

	filters = {
		"default_service_level_agreement": service_level_agreement.default_service_level_agreement,
		"service_level": service_level_agreement.service_level,
	}

	if not default_service_level_agreement:
		filters.update({"entity_type": entity_type, "entity": entity})

	sla = frappe.db.exists("Service Level Agreement", filters)
	if sla:
		frappe.delete_doc("Service Level Agreement", sla, force=1)

	return frappe.get_doc(service_level_agreement).insert(
		ignore_permissions=True, ignore_if_duplicate=True
	)


def create_customer():
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": "_Test Customer",
			"customer_group": "Commercial",
			"customer_type": "Individual",
			"territory": "Rest Of The World",
		}
	)
	if not frappe.db.exists("Customer", "_Test Customer"):
		customer.insert(ignore_permissions=True)
		return customer.name
	else:
		return frappe.db.exists("Customer", "_Test Customer")


def create_customer_group():
	customer_group = frappe.get_doc(
		{"doctype": "Customer Group", "customer_group_name": "_Test SLA Customer Group"}
	)

	if not frappe.db.exists("Customer Group", {"customer_group_name": "_Test SLA Customer Group"}):
		customer_group.insert()
		return customer_group.name
	else:
		return frappe.db.exists("Customer Group", {"customer_group_name": "_Test SLA Customer Group"})


def create_territory():
	territory = frappe.get_doc(
		{
			"doctype": "Territory",
			"territory_name": "_Test SLA Territory",
		}
	)

	if not frappe.db.exists("Territory", {"territory_name": "_Test SLA Territory"}):
		territory.insert()
		return territory.name
	else:
		return frappe.db.exists("Territory", {"territory_name": "_Test SLA Territory"})


def create_service_level_agreements_for_issues():
	create_service_level_agreement(
		default_service_level_agreement=1,
		holiday_list="__Test Holiday List",
		entity_type=None,
		entity=None,
		response_time=14400,
		resolution_time=21600,
	)

	create_customer()
	create_service_level_agreement(
		default_service_level_agreement=0,
		holiday_list="__Test Holiday List",
		entity_type="Customer",
		entity="_Test Customer",
		response_time=7200,
		resolution_time=10800,
	)

	create_customer_group()
	create_service_level_agreement(
		default_service_level_agreement=0,
		holiday_list="__Test Holiday List",
		entity_type="Customer Group",
		entity="_Test SLA Customer Group",
		response_time=7200,
		resolution_time=10800,
	)

	create_territory()
	create_service_level_agreement(
		default_service_level_agreement=0,
		holiday_list="__Test Holiday List",
		entity_type="Territory",
		entity="_Test SLA Territory",
		response_time=7200,
		resolution_time=10800,
	)

	create_service_level_agreement(
		default_service_level_agreement=0,
		holiday_list="__Test Holiday List",
		entity_type=None,
		entity=None,
		response_time=14400,
		resolution_time=21600,
		service_level="24-hour-SLA",
		start_time="00:00:00",
		end_time="23:59:59",
		condition="doc.issue_type == 'Critical'",
	)


def make_holiday_list():
	holiday_list = frappe.db.exists("Holiday List", "__Test Holiday List")
	if not holiday_list:
		holiday_list = frappe.get_doc(
			{
				"doctype": "Holiday List",
				"holiday_list_name": "__Test Holiday List",
				"from_date": "2019-01-01",
				"to_date": "2019-12-31",
				"holidays": [
					{"description": "Test Holiday 1", "holiday_date": "2019-03-05"},
					{"description": "Test Holiday 2", "holiday_date": "2019-03-07"},
					{"description": "Test Holiday 3", "holiday_date": "2019-02-11"},
				],
			}
		).insert()


def create_custom_doctype():
	if not frappe.db.exists("DocType", "Test SLA on Custom Dt"):
		doc = frappe.get_doc(
			{
				"doctype": "DocType",
				"module": "Support",
				"custom": 1,
				"fields": [
					{"label": "Date", "fieldname": "date", "fieldtype": "Date"},
					{"label": "Description", "fieldname": "desc", "fieldtype": "Long Text"},
					{"label": "Email ID", "fieldname": "email_id", "fieldtype": "Link", "options": "Customer"},
					{
						"label": "Status",
						"fieldname": "status",
						"fieldtype": "Select",
						"options": "Open\nReplied\nClosed",
					},
				],
				"permissions": [{"role": "System Manager", "read": 1, "write": 1}],
				"name": "Test SLA on Custom Dt",
			}
		)
		doc.insert()
		return doc
	else:
		return frappe.get_doc("DocType", "Test SLA on Custom Dt")


def make_lead(creation=None, index=0, company=None):
	return frappe.get_doc(
		{
			"doctype": "Lead",
			"email_id": "test_lead1@example{0}.com".format(index),
			"lead_name": "_Test Lead {0}".format(index),
			"status": "Open",
			"creation": creation,
			"service_level_agreement_creation": creation,
			"priority": "Medium",
			"company": company,
		}
	).insert(ignore_permissions=True)
