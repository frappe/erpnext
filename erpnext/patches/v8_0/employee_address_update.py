# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	move_employee_address_to_address()

def move_employee_address_to_address():
	employee_addresses = frappe.db.sql("""select name, employee_name, company, permanent_accommodation_type, 
		current_accommodation_type, current_address, permanent_address from tabEmployee 
		where 
			(permanent_address is not null and permanent_address != '') or 
			(current_address is not null and current_address !='')""", as_dict=1)	
	
	for employee_address in employee_addresses:
		if employee_address.permanent_address:
			permanent_address = get_formatted_address(employee_address.permanent_address)

			create_new_address(employee_address.name, employee_address.employee_name, permanent_address, 
				employee_address.company, "Permanent", employee_address.permanent_accommodation_type)

		if employee_address.current_address:
			current_address = get_formatted_address(employee_address.current_address)

			create_new_address(employee_address.name, employee_address.employee_name, current_address, 
				employee_address.company, "Current", employee_address.current_accommodation_type)

def get_formatted_address(address):
	formatted_address = frappe._dict()
	address_lines = address.split("\n")
	address_lines = [x.strip().replace(',','') for x in address_lines if x.strip()]

	formatted_address.address_line1 = address_lines[0]

	if len(address_lines) == 1:
		formatted_address.city = address_lines[0]

	if len(address_lines) == 2:
		formatted_address.city = address_lines[1]

	if len(address_lines) > 2:
		formatted_address.address_line2 = address_lines[1]
		formatted_address.city = address_lines[2]

		if len(address_lines) == 3:
			if any(i.isdigit() for i in address_lines[-1]):
				formatted_address.pincode = address_lines[-1]
			else:
				formatted_address.country = address_lines[-1]
		else:
			if any(i.isdigit() for i in address_lines[-1]):
				formatted_address.pincode = address_lines[-1]
				formatted_address.country = address_lines[-2]
			else:
				formatted_address.country = address_lines[-1]

		if len(address_lines) > 5:
			formatted_address.state = address_lines[-3]

		if len(address_lines) > 6:
			formatted_address.county = address_lines[-4] 		
	return formatted_address

def create_new_address(name, employee_name, address, company, address_type, accomodation_type = None):
	new_address = frappe.new_doc("Address")
	new_address.address_title = employee_name
	if accomodation_type:
		new_address.address_title = employee_name +"-"+ accomodation_type
	new_address.address_type = address_type
	new_address.address_line1 = address.address_line1
	new_address.city = address.city
	new_address.address_line2 = address.address_line2 or ''
	new_address.pincode = address.pincode or ''
	new_address.country = address.country or frappe.get_value('Company', company, 'country')
	new_address.state = address.state or ''
	new_address.county = address.county or ''
	new_address.append('links', { "link_doctype": "Employee", "link_name": name })
	new_address.flags.ignore_mandatory = True
	new_address.flags.ignore_validate = True
	new_address.insert()