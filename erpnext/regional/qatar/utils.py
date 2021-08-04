from __future__ import unicode_literals
import frappe
import os
import csv
import itertools
from frappe.utils import comma_and, get_link_to_form, get_datetime
from frappe import _

from erpnext.regional.doctype.salary_information_file.salary_information_file import get_company_bank_details
from erpnext.hr.doctype.attendance.attendance import get_month_map

frequency = {
	"Monthly": "M",
	"Bimonthly": "B"
}

def validate_payer_details(doc, method):
	if frappe.get_cached_value('Company', doc.company, 'country') == "Qatar":
		if doc.payer_establishment_id:
			mandatory_fields = []
			if not doc.payer_bank:
				mandatory_fields.append("Bank")
			if not doc.payer_bank_short_name:
				mandatory_fields.append("Bank Short Name")
			if not doc.iban:
				mandatory_fields.append("IBAN")

			if len(mandatory_fields):
				frappe.throw(_("fill {0} in {1} or leave it blank if Employer is Payer").format(
					comma_and(mandatory_fields), get_link_to_form("Company", doc.company)
			))

def validate_bank_details_and_generate_csv(doc, method):
	if frappe.get_cached_value('Company', doc.company, 'country') == "Qatar":
		if not doc.payer_establishment_id:
			company_bank_details = get_company_bank_details(doc.company)

		if len(company_bank_details):
			company_bank_details = company_bank_details[0]

		sif_header_column = get_sif_header_column()
		sif_records_column = get_sif_records_column()

		employee_records, missing_fields_for_employee, total_salaries = get_sif_record_data(doc.month, doc.year, doc.company)

		sif_header_data = get_sif_header_data(doc, company_bank_details)
		sif_header_data.append(total_salaries)
		sif_header_data.append(len(employee_records))

		if not missing_fields_for_employee:
			doc.number_of_records = len(employee_records)
			generate_csv(sif_header_column, sif_header_data, sif_records_column, employee_records, doc.name)
			create_and_attach_file(doc)
		else:
			frappe.throw("Hello")

def generate_csv(sif_header_column, sif_header_data, sif_records_column, employee_records, name):
	site_path = frappe.utils.get_site_path()

	with open(site_path + '/public/files/'+name+'.csv', 'w+', newline='') as file:
		writer = csv.writer(file)
		writer.writerow(sif_header_column)
		writer.writerow(sif_header_data)
		writer.writerow(sif_records_column)

		for idx, record in enumerate(employee_records):
			id = str(idx+1)
			record_id = '0'*(6-len(id))+id
			#according to standard it will be like, 000001, 000002
			record.insert(0, record_id)
			writer.writerow(record)

def create_and_attach_file(doc):
	file_name = doc.name+".csv"
	file = frappe.new_doc("File")
	file.attached_to_doctype = "Salary information file"
	file.attached_to_name = doc.name
	file.file_name = file_name
	file.file_url = "/files/"+file_name
	file.folder = "Home"
	file.is_private = 0
	file.save()


def get_sif_header_column():
	return ["Employer EID", "File Creation Date", "File Creation Time", "Payer EID", "Payer QID", "Payer Bank"
		"Short Name", "Payer IBAN", "Salary Year and Month", "Total Salaries", "Total Records", "SIF Version"]

def get_sif_records_column():
	return ["Record Sequence", "Employee QID", "Employee Visa ID", "Employee Name", "Employee Bank Short Name",
	"Employee Account", "Salary Frequency", "Number of Working days", "Net Salary", "Basic Salary",
	"Extra hours", "Extra income", "Deductions", "Payment Type", "Notes / Comments", "Housing Allowance",
	"Food Allowance", "Transportation Allowance", "Over Time Allowance", "Deduction Reason Code",
	"Extra Field 1", "Extra Field 2"]

def get_sif_header_data(doc, company_bank_details):
	if doc.payer_establishment_id:
		bank_short_name = doc.payer_bank_short_name
		iban = doc.iban
	else:
		bank_short_name = frappe.db.get_value(
			"Bank", company_bank_details.bank, "bank_short_name")
		iban = company_bank_details.iban

	month = get_month_map()[doc.month]
	if month < 10:
		month = '0'+str(month)
	else:
		month = str(month)
	year_month = str(doc.year) + month # as per format yyyyMM

	row = [
		doc.employer_establishment_id,
		get_datetime(doc.creation_date).strftime("%Y%m%d"),
		get_datetime(doc.creation_time).strftime("%H%M"),
		doc.payer_establishment_id if doc.payer_establishment_id else doc.employer_establishment_id,
		doc.payer_qid if doc.payer_establishment_id else '',
		bank_short_name,
		iban,
		year_month,
	]
	return row


def get_sif_record_data(month, year, company):
	total_salaries = 0
	missing_fields_for_employee = {}
	employee_records = []
	month = get_month_map()[month]

	data = itertools.groupby(get_salary_slip(month, year, company), key=lambda x: (x['employee']))

	for employee, group in data:
		employee_detail = get_employee_data(employee)

		if not (employee_detail.residential_id or employee_detail.visa_id):
			missing_fields_for_employee = set_missing_fields_data(employee, "Residential ID or Visa ID", missing_fields_for_employee)

		if not employee_detail.bank_abbr:
			missing_fields_for_employee = set_missing_fields_data(employee, "Bank Short/Abbr", missing_fields_for_employee)

		if not employee_detail.bank_ac_no:
			missing_fields_for_employee = set_missing_fields_data(employee, "Bank A/c No.", missing_fields_for_employee)

		group = list(group)

		basic_components = get_basic_components()
		housing_components = get_housing_allowance_components()
		food_allowance_components = get_food_allowance_components()
		transpotation_components = get_transpotation_components()

		payroll_frequency = group[0]["payroll_frequency"]

		basic_amount = get_total_component_amount(group, basic_components)
		housing_allowance_amount = get_total_component_amount(group, housing_components)
		food_allowance_amount = get_total_component_amount(group, food_allowance_components)
		transpotation_allowance_amount = get_total_component_amount(group, transpotation_components)

		row = [
			employee_detail.residential_id,
			employee_detail.visa_id if not employee_detail.residential_id else '',
			employee_detail.employee_name,
			employee_detail.bank_abbr,
			employee_detail.bank_ac_no,
			frequency.get(payroll_frequency, ''),
			group[0]["total_working_days"],
			group[0]["net_pay"],
			basic_amount,
			'', # Extra Hour will be updated after Overtime PR merge
			group[0]["gross_pay"] - basic_amount,
			group[0]["total_deduction"],
			'',
			'', # for comments
			housing_allowance_amount,
			food_allowance_amount,
			transpotation_allowance_amount,
			'', # Overtime Allowance will be updated after Overtime PR merge
			'', # reason for Deduction
			'', # extra  Field 1
			'', # extra  Field 2
		]

		employee_records.append(row)
		total_salaries += group[0]["net_pay"]

	return employee_records, missing_fields_for_employee, total_salaries

def set_missing_fields_data(key, field, missing_fields_for_employee):
	if key not in missing_fields_for_employee.keys():
		missing_fields_for_employee[key] = [field]
	else:
		missing_fields_for_employee[key].append(field)

	return missing_fields_for_employee


def get_salary_slip(month, year, company):
	return frappe.db.sql("""SELECT ss.name, ss.employee, ss.payroll_frequency, ss.total_deduction,
		ss.total_working_days, ss.net_pay, sd.parentfield, sd.salary_component, sd.amount, ss.gross_pay,
		ss.start_date, ss.end_date, ss.leave_without_pay
		FROM `tabSalary Slip` as ss, `tabSalary Detail` as sd
		WHERE sd.parent = ss.name
		AND MONTH(ss.start_date) = %(month)s
		AND YEAR(ss.start_date) = %(year)s
		AND ss.docstatus = 1
	""", {"month": month, "year": year}, as_dict=1)


def get_basic_components():
	basic_components = frappe.get_all("Salary Component", filters = {"is_basic": 1})
	basic_components = [d.name for d in basic_components]
	if not len(basic_components):
		frappe.throw(_("No Basic Salary Component Found"))

	return basic_components

def get_housing_allowance_components():
	return frappe.get_all("Salary Component", filters = {"is_housing_allowance": 1}, as_list=1)

def get_food_allowance_components():
	return frappe.get_all("Salary Component", filters = {"is_food_allowance": 1}, as_list=1)

def get_transpotation_components():
	return frappe.get_all("Salary Component", filters = {"is_transpotation_allowance": 1}, as_list=1)

def get_total_component_amount(data, component_list):
	amount = [d.amount for d in data if d.salary_component in component_list]
	amount = sum(amount) if len(amount) else 0

	return amount

def get_employee_data(employee):
	return frappe.db.get_value("Employee", employee, ["residential_id", "visa_id", "employee_name",
		"bank_abbr", "bank_ac_no"], as_dict=1)


