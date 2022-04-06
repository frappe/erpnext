# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json

import frappe
from frappe import _
from frappe.utils import cint, cstr
from frappe.utils.nestedset import NestedSet


class HealthcareServiceUnit(NestedSet):
	nsm_parent_field = "parent_healthcare_service_unit"

	def validate(self):
		self.set_service_unit_properties()

	def autoname(self):
		if self.company:
			suffix = " - " + frappe.get_cached_value("Company", self.company, "abbr")
			if not self.healthcare_service_unit_name.endswith(suffix):
				self.name = self.healthcare_service_unit_name + suffix
		else:
			self.name = self.healthcare_service_unit_name

	def on_update(self):
		super(HealthcareServiceUnit, self).on_update()
		self.validate_one_root()

	def set_service_unit_properties(self):
		if cint(self.is_group):
			self.allow_appointments = False
			self.overlap_appointments = False
			self.inpatient_occupancy = False
			self.service_unit_capacity = 0
			self.occupancy_status = ""
			self.service_unit_type = ""
		elif self.service_unit_type != "":
			service_unit_type = frappe.get_doc("Healthcare Service Unit Type", self.service_unit_type)
			self.allow_appointments = service_unit_type.allow_appointments
			self.inpatient_occupancy = service_unit_type.inpatient_occupancy

			if self.inpatient_occupancy and self.occupancy_status != "":
				self.occupancy_status = "Vacant"

			if service_unit_type.overlap_appointments:
				self.overlap_appointments = True
			else:
				self.overlap_appointments = False
				self.service_unit_capacity = 0

		if self.overlap_appointments:
			if not self.service_unit_capacity:
				frappe.throw(
					_("Please set a valid Service Unit Capacity to enable Overlapping Appointments"),
					title=_("Mandatory"),
				)


@frappe.whitelist()
def add_multiple_service_units(parent, data):
	"""
	parent - parent service unit under which the service units are to be created
	data (dict) - company, healthcare_service_unit_name, count, service_unit_type, warehouse, service_unit_capacity
	"""
	if not parent or not data:
		return

	data = json.loads(data)
	company = (
		data.get("company")
		or frappe.defaults.get_defaults().get("company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
	)

	if not data.get("healthcare_service_unit_name") or not company:
		frappe.throw(
			_("Service Unit Name and Company are mandatory to create Healthcare Service Units"),
			title=_("Missing Required Fields"),
		)

	count = cint(data.get("count") or 0)
	if count <= 0:
		frappe.throw(
			_("Number of Service Units to be created should at least be 1"),
			title=_("Invalid Number of Service Units"),
		)

	capacity = cint(data.get("service_unit_capacity") or 1)

	service_unit = {
		"doctype": "Healthcare Service Unit",
		"parent_healthcare_service_unit": parent,
		"service_unit_type": data.get("service_unit_type") or None,
		"service_unit_capacity": capacity if capacity > 0 else 1,
		"warehouse": data.get("warehouse") or None,
		"company": company,
	}

	service_unit_name = "{}".format(data.get("healthcare_service_unit_name").strip(" -"))

	last_suffix = frappe.db.sql(
		"""SELECT
		IFNULL(MAX(CAST(SUBSTRING(name FROM %(start)s FOR 4) AS UNSIGNED)), 0)
		FROM `tabHealthcare Service Unit`
		WHERE name like %(prefix)s AND company=%(company)s""",
		{
			"start": len(service_unit_name) + 2,
			"prefix": "{}-%".format(service_unit_name),
			"company": company,
		},
		as_list=1,
	)[0][0]
	start_suffix = cint(last_suffix) + 1

	failed_list = []
	for i in range(start_suffix, count + start_suffix):
		# name to be in the form WARD-####
		service_unit["healthcare_service_unit_name"] = "{}-{}".format(
			service_unit_name, cstr("%0*d" % (4, i))
		)
		service_unit_doc = frappe.get_doc(service_unit)
		try:
			service_unit_doc.insert()
		except Exception:
			failed_list.append(service_unit["healthcare_service_unit_name"])

	return failed_list
