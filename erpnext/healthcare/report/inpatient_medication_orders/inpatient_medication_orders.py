# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe

from erpnext.healthcare.doctype.inpatient_medication_entry.inpatient_medication_entry import (
	get_current_healthcare_service_unit,
)


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)

	return columns, data, None, chart


def get_columns():
	return [
		{
			"fieldname": "patient",
			"fieldtype": "Link",
			"label": "Patient",
			"options": "Patient",
			"width": 200,
		},
		{
			"fieldname": "healthcare_service_unit",
			"fieldtype": "Link",
			"label": "Healthcare Service Unit",
			"options": "Healthcare Service Unit",
			"width": 150,
		},
		{
			"fieldname": "drug",
			"fieldtype": "Link",
			"label": "Drug Code",
			"options": "Item",
			"width": 150,
		},
		{"fieldname": "drug_name", "fieldtype": "Data", "label": "Drug Name", "width": 150},
		{
			"fieldname": "dosage",
			"fieldtype": "Link",
			"label": "Dosage",
			"options": "Prescription Dosage",
			"width": 80,
		},
		{
			"fieldname": "dosage_form",
			"fieldtype": "Link",
			"label": "Dosage Form",
			"options": "Dosage Form",
			"width": 100,
		},
		{"fieldname": "date", "fieldtype": "Date", "label": "Date", "width": 100},
		{"fieldname": "time", "fieldtype": "Time", "label": "Time", "width": 100},
		{"fieldname": "is_completed", "fieldtype": "Check", "label": "Is Order Completed", "width": 100},
		{
			"fieldname": "healthcare_practitioner",
			"fieldtype": "Link",
			"label": "Healthcare Practitioner",
			"options": "Healthcare Practitioner",
			"width": 200,
		},
		{
			"fieldname": "inpatient_medication_entry",
			"fieldtype": "Link",
			"label": "Inpatient Medication Entry",
			"options": "Inpatient Medication Entry",
			"width": 200,
		},
		{
			"fieldname": "inpatient_record",
			"fieldtype": "Link",
			"label": "Inpatient Record",
			"options": "Inpatient Record",
			"width": 200,
		},
	]


def get_data(filters):
	conditions, values = get_conditions(filters)

	data = frappe.db.sql(
		"""
		SELECT
			parent.patient, parent.inpatient_record, parent.practitioner,
			child.drug, child.drug_name, child.dosage, child.dosage_form,
			child.date, child.time, child.is_completed, child.name
		FROM `tabInpatient Medication Order` parent
		INNER JOIN `tabInpatient Medication Order Entry` child
		ON child.parent = parent.name
		WHERE
			parent.docstatus = 1
			{conditions}
		ORDER BY date, time
	""".format(
			conditions=conditions
		),
		values,
		as_dict=1,
	)

	data = get_inpatient_details(data, filters.get("service_unit"))

	return data


def get_conditions(filters):
	conditions = ""
	values = dict()

	if filters.get("company"):
		conditions += " AND parent.company = %(company)s"
		values["company"] = filters.get("company")

	if filters.get("from_date") and filters.get("to_date"):
		conditions += " AND child.date BETWEEN %(from_date)s and %(to_date)s"
		values["from_date"] = filters.get("from_date")
		values["to_date"] = filters.get("to_date")

	if filters.get("patient"):
		conditions += " AND parent.patient = %(patient)s"
		values["patient"] = filters.get("patient")

	if not filters.get("show_completed_orders"):
		conditions += " AND child.is_completed = 0"

	return conditions, values


def get_inpatient_details(data, service_unit):
	service_unit_filtered_data = []

	for entry in data:
		entry["healthcare_service_unit"] = get_current_healthcare_service_unit(entry.inpatient_record)
		if entry.is_completed:
			entry["inpatient_medication_entry"] = get_inpatient_medication_entry(entry.name)

		if (
			service_unit and entry.healthcare_service_unit and service_unit != entry.healthcare_service_unit
		):
			service_unit_filtered_data.append(entry)

		entry.pop("name", None)

	for entry in service_unit_filtered_data:
		data.remove(entry)

	return data


def get_inpatient_medication_entry(order_entry):
	return frappe.db.get_value(
		"Inpatient Medication Entry Detail", {"against_imoe": order_entry}, "parent"
	)


def get_chart_data(data):
	if not data:
		return None

	labels = ["Pending", "Completed"]
	datasets = []

	status_wise_data = {"Pending": 0, "Completed": 0}

	for d in data:
		if d.is_completed:
			status_wise_data["Completed"] += 1
		else:
			status_wise_data["Pending"] += 1

	datasets.append(
		{
			"name": "Inpatient Medication Order Status",
			"values": [status_wise_data.get("Pending"), status_wise_data.get("Completed")],
		}
	)

	chart = {"data": {"labels": labels, "datasets": datasets}, "type": "donut", "height": 300}

	chart["fieldtype"] = "Data"

	return chart
