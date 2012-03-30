# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# long patches
import webnotes

def set_subjects_and_tagfields():
	subject_dict = {
		'Item':'%(item_name)s',
		'Customer':' ',
		'Contact':'%(first_name)s %(last_name)s - Email: %(email_id)s | Contact: %(contact_no)s',
		'Supplier':' ',
		'Lead':'%(lead_name)s from %(company_name)s | To Discuss: %(to_discuss)s',
		'Quotation':'To %(customer_name)s on %(transaction_date)s worth %(currency)s %(grand_total_export)s',
		'Opportunity':'To %(customer_name)s%(lead_name)s on %(transaction_date)s',
		'Sales Order':'From %(customer_name)s on %(transaction_date)s worth %(currency)s %(grand_total_export)s | %(per_delivered)s% delivered | %(per_billed)s% billed',
		'Delivery Note':'To %(customer_name)s on %(transaction_date)s | %(per_billed)s% billed',
		'Purchase Request':'%(per_ordered)s% ordered',
		'Purchase Order':'To %(supplier_name)s on %(transaction_date)s | %(per_received)s% delivered',
		'Purchase Receipt':'From %(supplier_name)s against %(purchase_order)s on %(transaction_date)s',
		'Sales Invoice':'To %(customer_name)s worth %(currency)s %(grand_total_export)s due on %(due_date)s | %(outstanding_amount)s outstanding',
		'Purchase Invoice':'From %(supplier_name)s due on %(due_date)s | %(outstanding_amount)s outstanding',
		'Journal Voucher':' ',
		'Serial No':'%(item_code)s',
		'Project':' ',
		'Task':'%(subject)s',
		'Timesheet':'%(owner)s',
		'Support Ticket':'%(problem_description)s',
		'Installation Note':'At %(customer_name)s on %(inst_date)s',
		'Maintenance Visit':'To %(customer_name)s on %(mntc_date)s',
		'Customer Issue':'%(complaint)s By %(complaint_raised_by)s on %(issue_date)s',
		'Employee':'%(employee_name)s',
		'Expense Claim':'From %(employee_name)s for %(total_claimed_amount)s (claimed)',
		'Appraisal':'',
		'Leave Application':'From %(employee_name)s, %(designation)s',
		'Salary Structure':'For %(employee_name)s',
		'Salary Slip':'For %(employee_name)s, %(designation)s',
		'Bill of Materials':'%(item_code)s'
	}
	
	tags_dict = {
		'Item':'item_group',
		'Customer':'customer_group,customer_type',
		#'Contact':'',
		'Supplier':'supplier_type',
		'Lead':'status,source',
		'Quotation':'status',
		'Opportunity':'',
		'Sales Order':'status',
		'Delivery Note':'',
		'Purchase Request':'',
		'Purchase Order':'',
		'Purchase Receipt':'',
		'Sales Invoice':'',
		'Purchase Invoice':'',
		'Journal Voucher':'voucher_type',
		'Serial No':'status',
		'Project':'status',
		'Task':'status',
		'Timesheet':'',
		'Support Ticket':'',
		'Installation Note':'',
		'Maintenance Visit':'completion_status,maintenance_type',
		'Customer Issue':'status',
		'Employee':'status',
		'Expense Claim':'approval_status',
		'Appraisal':'',
		'Leave Application':'leave_type',
		'Salary Structure':'',
		'Bill of Materials':''
	}
	
	description_dict = {
		'Property Setter':'Property Setter overrides a standard DocType or Field property',
		'Custom Field':'Adds a custom field to a DocType',
		'Custom Script':'Adds a custom script (client or server) to a DocType'
	}
	
	alldt = []
	
	for dt in subject_dict:
		webnotes.conn.sql('update tabDocType set subject=%s where name=%s', (subject_dict[dt], dt))
		if not dt in alldt: alldt.append(dt)
	
	for dt in tags_dict:
		webnotes.conn.sql('update tabDocType set tag_fields=%s where name=%s', (tags_dict[dt], dt))
		if not dt in alldt: alldt.append(dt)

	for dt in description_dict:
		webnotes.conn.sql('update tabDocType set description=%s where name=%s', (description_dict[dt], dt))
		if not dt in alldt: alldt.append(dt)
	
	#from webnotes.modules.export_module import export_to_files
	#for dt in alldt:
	#	export_to_files(record_list=[['DocType',dt]])

def support_patch():
	# relaod support and other doctypes
	
	from webnotes.modules import reload_doc
	
	webnotes.model.delete_doc('DocType','Support Ticket')
	reload_doc('setup','doctype','support_email_settings')
	reload_doc('support','doctype','support_ticket')
	reload_doc('support','doctype','support_ticket_response')
