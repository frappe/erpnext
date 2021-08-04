# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.permissions import add_permission, update_permission_property

def setup(company=None, patch=True):
	make_custom_fields()
	add_roles_and_permission_for_wps()

def make_custom_fields():
	wps_fields_for_company = get_wps_fields_for_company()
	wps_fields_for_salary_component = get_wps_fields_for_salary_component()
	wps_fields_for_sif = get_wps_fields_for_sif()

	custom_fields = {
		'Company': wps_fields_for_company,
		'Salary Component': wps_fields_for_salary_component,
		'Salary Information File': wps_fields_for_sif
	}
	create_custom_fields(custom_fields)

def add_roles_and_permission_for_wps():
	doctype = "Salary Information File"
	add_permission(doctype, 'All', 0)
	for role in ('HR Manager', 'HR User', 'System Manager'):
		add_permission(doctype, role, 0)
		update_permission_property(doctype, role, 0, 'write', 1)
		update_permission_property(doctype, role, 0, 'create', 1)
		update_permission_property(doctype, role, 0, 'submit', 1)
		update_permission_property(doctype, role, 0, 'cancel', 1)
		update_permission_property(doctype, role, 0, 'Amend', 1)

def get_wps_fields_for_company():
	description_for_payer_eid = "The Employer and Payer Establishment ID can be same if Employer pays to its employees directly"
	wps_fields_for_company = [
		dict(fieldname='employer_establishment_id', label='Employer Establishment ID',
			fieldtype='Data', insert_after='date_of_establishment', print_hide=1),
		dict(fieldname='payer_details', label='Payer Details',
			fieldtype='Section Break', insert_after='employer_establishment_id', print_hide=1),
		dict(fieldname='payer_establishment_id', label='Payer Establishment ID',
			fieldtype='Data', insert_after='payer_details', print_hide=1,
			description=description_for_payer_eid),
		dict(fieldname='payer_qid', label='Payer QID',
			fieldtype='Data', insert_after='payer_establishment_id', print_hide=1),
		dict(fieldname='payer_bank', label='Bank',
			fieldtype='Data', insert_after='payer_qid', print_hide=1),
		dict(fieldname='col_break_wps', label='',
			fieldtype='Column Break', insert_after='payer_bank', print_hide=1),
		dict(fieldname='payer_bank_short_name', label='Bank Short Name',
			fieldtype='Data', insert_after='col_break_wps', print_hide=1),
		dict(fieldname='iban', label='IBAN',
			fieldtype='Data', insert_after='payer_bank_short_name', print_hide=1),
	]

	return wps_fields_for_company

def get_wps_fields_for_salary_component():
	wps_fields_for_salary_structure = [
		dict(fieldname='is_housing_allowance', label='Is Housing Allowance',
			fieldtype='Check', insert_after='is_income_tax_component', print_hide=1),
		dict(fieldname='is_food_allowance', label='Is Food Allowance',
			fieldtype='Check', insert_after='is_housing_allowance', print_hide=1),
		dict(fieldname='is_transpotation_allowance', label='Is Transpotation Allowance ',
			fieldtype='Check', insert_after='is_food_allowance', print_hide=1),
		dict(fieldname='is_basic', label='Is Basic',
			fieldtype='Check', insert_after='is_transpotation_allowance', print_hide=1)
	]
	return wps_fields_for_salary_structure

def get_wps_fields_for_sif():
	wps_fields_for_sif = [
		dict(fieldname='payer_details', label='Payer Details',
			fieldtype='Section Break', insert_after='number_of_records', print_hide=1),
		dict(fieldname='payer_establishment_id', label='Payer Establishment ID',
			fieldtype='Data', insert_after='payer_details', print_hide=1, read_only=1,
			description="Leave blank if Employer is Payer", fetch_from = "company.payer_establishment_id"),
		dict(fieldname='payer_qid', label='Payer QID', read_only=1,
			fieldtype='Data', insert_after='payer_establishment_id',
			fetch_from= "company.payer_qid", print_hide=1),
		dict(fieldname='payer_bank', label='Bank',
			fieldtype='Data', insert_after='payer_qid', read_only=1,
			fetch_from= "company.payer_bank", print_hide=1),
		dict(fieldname='col_break_wps', label='',
			fieldtype='Column Break', insert_after='payer_bank', print_hide=1),
		dict(fieldname='payer_bank_short_name', label='Bank Short Name',
			fieldtype='Data', insert_after='col_break_wps', read_only=1,
			fetch_from= "company.payer_bank_short_name", print_hide=1),
		dict(fieldname='iban', label='IBAN', read_only=1,
			fieldtype='Data', insert_after='payer_bank_short_name',
			fetch_from= "company.iban", print_hide=1),
	]

	return wps_fields_for_sif


