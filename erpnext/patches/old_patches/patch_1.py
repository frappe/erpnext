"""
	Old patches for reference
"""

if patch_no==33:
	pass
elif patch_no==34:
	webnotes.conn.sql("update `tabDocField` set options = 'Letter Head', print_hide = 1 where fieldname = 'letter_head' and fieldtype = 'Link'")
elif patch_no==35:
	webnotes.conn.sql("update tabDocType set module = 'Event Updates' where name = 'Feed Control'")
elif patch_no==36:
	# remove delivery note foreign key in Serial Number
	from webnotes.model.db_schema import DbTable
	t = DbTable('Serial No')
	fk_list  = t.get_foreign_keys()
	for f in fk_list:
		if f[0]=='delivery_note_no':
			webnotes.conn.commit()
			webnotes.conn.sql("alter table `tabSerial No` drop foreign key `%s`" % f[1])
			webnotes.conn.begin()
			webnotes.conn.sql("update tabDocField set fieldtype='Data' where fieldname='delivery_note_no' and parent='Serial No' limit 1")
elif patch_no==37:
	import os
	mod_path = webnotes.defs.modules_path
	path_list = []
	for m in os.listdir(mod_path):
		for t in ['doctype', 'page', 'search_criteria']:
			dt_path = os.path.join(mod_path, m, t)
			if os.path.exists(dt_path):
				for dt in os.listdir(dt_path):
					if '.' not in dt and os.path.exists(os.path.join(dt_path, dt, dt+ '.txt')):
						path_list.append(os.path.join(dt_path, dt, dt+ '.txt'))

	for d in path_list:
		doclist = eval(open(d,'r').read())
		webnotes.conn.sql("update `tab%s` set module = '%s' where name = '%s'" % (doclist[0]['doctype'], doclist[0]['module'], doclist[0]['name']))

elif patch_no==38:
	import webnotes
	webnotes.conn.set_global("system_message", "System Updates: Hello! You would have noticed some changes on the Home Page. As a part of our commitment to make the system more friendly and social, we have re-designed the feed so that now you will only see feed that is relevant to you (either you have created something or you have been mentioned in the document).<br><br>On the individual listings, you can add tags and also color them!<br><br>You will also get time-to-time updates from our side here. Do keep sending your feedback at support@erpnext.com.")
	webnotes.conn.set_global("system_message_id", "1")

elif patch_no == 39:
	pass

elif patch_no == 40:
	import_from_files(record_list=[['material_management','doctype','item']])

elif patch_no == 42:
	acc = sql("select name, lft, rgt from tabAccount where account_name in ('Incomes', 'Expenses')")
	for d in acc:
		sql("update tabAccount set is_pl_account = 'Yes' where lft >= '%s' and rgt <= '%s'" % (d[1], d[2]))
elif patch_no == 43:
	import webnotes.model
	webnotes.model.delete_doc('Page', 'Module Manager')

# cleanup of Service, Customer Support, Utilities Modules
# -------------------------------------------------------
elif patch_no == 44:
	from webnotes.model import delete_doc

	for dt in sql("select name from tabDocType where module in ('Customer Support')"):
		delete_doc('DocType', dt[0])

	for dt in sql("select name from `tabSearch Criteria` where module in ('Customer Support')"):
		delete_doc('Search Criteria', dt[0])

	for dt in sql("select name from tabPage where module in ('Customer Support')"):
		delete_doc('Page', dt[0])

	# move a couple
	webnotes.conn.sql("update `tab%s` set module=%s where name=%s" % ('DocType', '%s', '%s'), ('Application Internal', 'Patch Util'))
	webnotes.conn.sql("update `tab%s` set module=%s where name=%s" % ('DocType', '%s', '%s'), ('Application Internal', 'DocType Property Setter'))

	# remove utilities
	webnotes.conn.sql('delete from `tabModule Def` where name in ("Customer Support", "Utilities")')

elif patch_no == 45:
	webnotes.conn.sql('delete from tabDocField where options="Ticket Response Detail"')

elif patch_no == 46:
	import webnotes
	webnotes.conn.set_global("system_message", "<b>SYSTEM DOWNTIME:</b> Hello! As part of our commitment to keep improving the service, we are planning a scheduled maintenance on our servers for 4 hrs on 16-Jan-2011(Sunday), from 10AM to 2PM. Do keep sending your feedback at support@erpnext.com.")
	webnotes.conn.set_global("system_message_id", "2")

elif patch_no == 47:
	import webnotes
	webnotes.conn.set_global("system_message", "")
	webnotes.conn.set_global("system_message_id", "3")

elif patch_no == 48:
	webnotes.conn.sql("update tabDocField set options = 'Print Heading' where fieldname = 'select_print_heading'")

elif patch_no == 49:
	webnotes.conn.sql("update tabDocType set autoname = '' where name = 'Search Criteria'")
elif patch_no == 50:
	sql("update tabDocField set in_filter = 1 where fieldname in ('cost_center', 'income_account', 'Item Group') and parent = 'RV Detail'")
elif patch_no == 51:
	sql("update tabDocField set options = 'link:Print Heading' where fieldtype = 'Select' and fieldname = 'select_print_heading' and parent = 'POS Setting'")
elif patch_no == 52:
	sql("update tabDocField set print_hide = 1 where fieldname = 'letter_head'")
elif patch_no == 53:
	sql("update tabDocType set search_fields = 'lead_name,lead_owner,status,contact_by,contact_date' where name = 'Lead'")
elif patch_no == 54:
	sql("delete from tabDocField where parent = 'Supplier' and label = 'Supplier Contacts' and fieldtype = 'Section Break'")
elif patch_no == 55:
	sql("commit")
	try:
		sql("alter table tabFeed add column `_user_tags` varchar(180)")
	except Exception, e:
		if e.args[0]!=1060:
			raise e
elif patch_no == 56:
	sql("delete from `tabModule Def Item` where parent = 'CRM' and doc_type = 'Reports' and doc_name = 'Delivery Note' and display_name = 'Territory, Item Group wise GP'")
elif patch_no == 57:
	import_from_files(record_list=[['selling','doctype','sales_order_detail']])

elif patch_no == 58:
	# module def patches
	sql("update `tabModule Def` set module_page = NULL where name not in ('Event Updates', 'Setup', 'My Company')")
	sql("delete from `tabModule Def Item` where doc_type in ('Separator', 'Setup Forms', 'More Reports')")
	sql("delete from `tabModule Def Item` where doc_name = 'Project Activity'")
	sql("update `tabModule Def` set module_label = 'People', disabled='No', is_hidden='No' where name = 'My Company'")

	# insert new module items
	from webnotes.model.doc import make_autoname
	if not sql("select name from `tabModule Def Item` where parent='Projects' and doc_name='Ticket'"):
		sql("""insert into `tabModule Def Item`
			(name, parent, parenttype, parentfield, docstatus, doc_type, doc_name, display_name, idx) values
			(%s, 'Projects', 'Module Def', 'items', 0, 'Forms', 'Ticket', 'Task', 1)""", make_autoname('MDI.#####'))

	if not sql("select name from `tabModule Def Item` where parent='Projects' and doc_name='Timesheet'"):
		sql("""insert into `tabModule Def Item`
			(name, parent, parenttype, parentfield, docstatus, doc_type, doc_name, display_name, idx) values
			(%s, 'Projects', 'Module Def', 'items', 0, 'Forms', 'Timesheet', 'Timesheet', 2)""", make_autoname('MDI.#####'))

	if not sql("select name from `tabModule Def Item` where parent='Projects' and doc_name='Projects'"):
		sql("""insert into `tabModule Def Item`
			(name, parent, parenttype, parentfield, docstatus, doc_type, doc_name, display_name, idx) values
			(%s, 'Projects', 'Module Def', 'items', 0, 'Pages', 'Projects', 'Gantt Chart', 1)""", make_autoname('MDI.#####'))

elif patch_no == 59:
	webnotes.conn.set_value('Control Panel',None,'mail_footer','')
	webnotes.conn.set_global('global_mail_footer','<div style="margin-top:8px; padding: 8px; font-size: 11px; text-align:right; border-top: 1px solid #AAA">Sent via <a href="https://www.erpnext.com">ERPNext</a></div>')
elif patch_no == 60:
	sql("delete from `tabModule Def Item` where display_name = 'Point of Sales'")
elif patch_no == 61:
	sql("delete from `tabTDS Category Account` where company not in (select name from tabCompany)")
elif patch_no == 62:
	# Import Supplier Quotation
	import_from_files(record_list=[['srm','doctype','supplier_quotation']])

	# Adding Status Filter
	sql("update tabDocType set search_fields = concat('status,',search_fields) where name IN ('Delivery Note','Leave Transaction')")
	# Import Other Charges

	import_from_files(record_list=[['setup','doctype','other_charges']])
elif patch_no == 63:
	sql("update `tabDocField` set permlevel = 1 where fieldname in ('return_date', 'return_details') and parent = 'Sales and Purchase Return Wizard'")
	import_from_files(record_list = [['accounts', 'doctype', 'rv_detail'], ['material_management', 'doctype', 'sales_and_purchase_return_wizard'], ['material_management', 'doctype', 'stock_entry']])

elif patch_no == 64:
	sql("update tabDocField set `hidden` = 1, `print_hide` = 1, `report_hide` = 1 where options in ('RFQ','Supplier Quotation')")
	sql("update tabDocType set `read_only` = 1, in_create = 1 where name in ('RFQ','Supplier Quotation')")
	sql("update tabDocField set `report_hide` = 0 where fieldname in ('email_id','phone_1','fax_1') and parent = 'Customer'")
elif patch_no == 65:
	# Monthly Trend Analyzer <-> Trend Analyzer
	sql("update `tabSearch Criteria` set criteria_name = 'Trend Analyzer' where criteria_name = 'Monthly Trend Analyzer' and name = 'SRCH/00159'")
	sql("update `tabModule Def Item` set display_name = 'Trend Analyzer' where parent = 'Analysis' and display_name = 'Monthly Trend Analyzer'")
elif patch_no == 66:
	import webnotes
	webnotes.conn.set_global("system_message", """<h3>UI Updates</h3>Based on user feedback, we have made a couple of changes in the UI:<ul><li>Sidebar menus are now collapsable</li><li>Forms are now scrollable (we removed the confusing tabs)</li><li>Feed is a lot more descriptive</li></ul>Do send us your feedback!""")
	webnotes.conn.set_global("system_message_id", "4")

	sql("update `tabModule Def Item` set doc_type = 'Setup Forms' where doc_name in ('TDS Payment', 'TDS Return Acknowledgement', 'Form 16A', 'Period Closing Voucher', 'IT Checklist')")
	from webnotes.session_cache import clear_cache
	clear_cache(webnotes.session['user'])
elif patch_no == 67:
	sql("update `tabDocField` set in_filter = 1 where fieldname = 'brand' and parent = 'RV Detail'")
	sql("delete from `tabModule Def Item` where (display_name = 'Sales Invoice' and parent = 'CRM') or (display_name = 'Purchase Invoice' and parent = 'SRM')")
elif patch_no == 68:
	from webnotes.modules.import_module import import_from_files
	import_from_files(record_list=[['hr','doctype','employee'],['roles','Role','Employee']])
elif patch_no == 69:
	# delete flds from employee master
	p = get_obj('Patch Util')
	emp_del_flds = ['month_of_birth']
	for f in emp_del_flds:
		p.delete_field('Employee', f)

	sql("Update tabDocField set `default` = 'Active' where fieldname = 'status' and parent = 'Employee'")

	# map parent flds
	fld_map = ['cell_number', 'personal_email', 'person_to_be_contacted', 'relation', 'emergency_phone_number', 'pan_number', 'passport_number', 'date_of_issue', 'valid_upto', 'place_of_issue', 'marital_status', 'blood_group', 'permanent_accommodation_type']

	emp_prof = sql("select t1.name, t1.employee, t1.permanent_address_line_1, t1.permanent_address_line_2, t1.city1, t1.state1, t1.country1, t1.pin_code1, t1.phn_no1, t1.present_address_line_1, t1.present_address_line_2, t1.city2, t1.state2, t1.country2, t1.pin_code2, t1.phn_no2, t1.fathers_name, t1.fathers_occupation, t1.mothers_name, t1.mothers_occupation, t1.spouses_name, t1.spouses_occupation, t1.height_cms, t1.weight_kgs, t1.allergies, t1.other_medical_concerns, t1.physical_handicap from `tabEmployee Profile` t1, `tabEmployee` t2 where t1.employee = t2.name")
	for e in emp_prof:
		prof_obj = get_obj('Employee Profile', e[0])
		emp_obj = get_obj('Employee', e[1])
		for d in fld_map:
			emp_obj.doc.fields[d] = prof_obj.doc.fields[d]
		emp_obj.doc.current_accommodation_type = prof_obj.doc.present_accommodation_type

		# address
		per_addr = cstr(e[2]) + '\n' + cstr(e[3]) + '\n' + cstr(e[4]) + '\n' + cstr(e[5]) + ', ' + cstr(e[6]) + '\n' + 'PIN - ' + cstr(e[7]) + '\n' + 'Ph. No' + cstr(e[8])
		cur_addr = cstr(e[9]) + '\n' + cstr(e[10]) + '\n' + cstr(e[11]) + '\n' + cstr(e[12]) + ', ' + cstr(e[13]) + '\n' + 'PIN - ' + cstr(e[14]) + '\n' + 'Ph. No' + cstr(e[15])
		emp_obj.doc.permanent_address = per_addr
		emp_obj.doc.current_address = cur_addr
		#family
		fam = "Father's Name: " + cstr(e[16]) + '\n' + "Father's Occupation: " + cstr(e[17]) + '\n' + "Mother's Name: " + cstr(e[18]) + '\n' + "Mother's Occupation: " + cstr(e[19]) + '\n' + "Spouse's Name: " + cstr(e[20]) + '\n' + "Spouse's Occupation: " + cstr(e[21])
		emp_obj.doc.family_background = fam
		# health
		health = 'Height(cms): ' + cstr(e[22]) + '\n' + 'Weight(kgs): ' + cstr(e[23]) + '\n' + 'Allergies: ' +cstr( e[24]) + '\n' + 'Other Medical Concern: ' + cstr(e[25]) + '\n' + 'Physically Handicapped(if any): ' + cstr(e[26])
		emp_obj.doc.health_details = health
		emp_obj.doc.save()


	# map tables
	tbl_list = ['Experience In Company Detail', 'Previous Experience Detail', 'Educational Qualifications Detail']
	for t in tbl_list:
		sql("update `tab%s` t1, `tabEmployee Profile` t2 set t1.parent = t2.employee, t1.parenttype = 'Employee' where t1.parent = t2.name" % t)


	# overwrite idx?????????


	# delete emp profile
	webnotes.model.delete_doc('DocType', 'Employee Profile')
	for e in emp_prof:
		webnotes.model.delete_doc('Employee Profile', e[0])

elif patch_no == 70:
	# update search criteria module -> System
	sql("update tabDocType set module='System' where name='Search Criteria'")

	# Cleanups to Contact
	sql("update tabDocField set fieldtype='Data' where options='Designation' and parent='Contact'")
	sql("update tabDocField set fieldtype='Data' where options='Department' and parent='Contact'")
	sql("update tabDocField set depends_on='eval:(cint(doc.is_customer) || cint(doc.is_supplier) || cint(doc.is_sales_partner))' where fieldname='is_primary_contact' and parent='Contact'")

	# import Contact, Employee
	from webnotes.modules.import_module import import_from_files
	import_from_files(record_list=[['utilities','doctype','contact']])


	# remove last_contact_date from Lead
	sql("delete from tabDocField where fieldname='last_contact_date' and parent='Lead'")

elif patch_no == 71:
	# Make Stock Qty and Conversion Factor field editable. Also no need to mention Conversion factor in table can do it directly
	sql("update `tabDocField` set `permlevel` = 0, `width` = '100px', `trigger` = 'Client' where parent IN ('PO Detail','Purchase Receipt Detail') and fieldname in ('stock_qty','conversion_factor')")
	sql("update `tabDocField` set `width` = '100px' where parent IN ('PO Detail','Purchase Receipt Detail') and fieldname = 'stock_uom'")

elif patch_no == 72:
	# Core Patch
	# ----------

	from webnotes.modules.import_module import import_from_files

	# import module def
	import_from_files(record_list = [['core', 'Module Def', 'Core']])
elif patch_no == 73:
	# set module in DocTypes
	sql("update tabDocType set module='Core' where name in ('DocType', 'DocField', 'DocPerm', 'Role', 'UserRole', 'Profile', 'Print Format', 'DocFormat', 'Control Panel', 'Event', 'Event Role', 'Event User', 'DefaultValue', 'Default Home Page', 'File', 'File Group', 'File Data', 'Letter Head', 'Module Def', 'Module Def Item', 'Module Def Role', 'Page', 'Page Role', 'Search Criteria', 'DocType Label', 'DocType Mapper', 'Field Mapper Detail', 'Table Mapper Detail')")

	# set module in Page
	sql("update tabPage set module='Core' where name='Login Page'")

	# move file browser to Tools
	sql("update tabPage set module='Tools' where name='File Browser'")
	sql("update tabDocType set module='Tools' where name='File Browser Control'")
	sql("update tabDocType set module='Application Internal' where name='Profile Control'")
elif patch_no == 74:
	p = get_obj('Patch Util')
	# permission
	p.delete_permission('Employee', 'Administrator', 0)
	p.delete_permission('Employee', 'Administrator', 1)
	p.add_permission('Employee', 'Employee', 0, read = 1, match = 'owner')
	p.add_permission('Employee', 'Employee', 1, read = 1, match = 'owner')
	sql("delete from `tabDocField` where parent = 'Employee' and label = 'Payroll Rule'")
elif patch_no == 75:
	#sal structure patch
	# import
	from webnotes.modules.import_module import import_from_files
	import_from_files(record_list=[['hr','doctype','salary_structure'], ['hr','doctype','earning_detail'],['hr','doctype','deduction_detail']])
elif patch_no == 76:
	# property
	p = get_obj('Patch Util')
	p.set_field_property('Salary Structure', 'is_active', 'default', 'Yes')
	p.set_field_property('Salary Structure', 'ctc', 'reqd', '1')
	p.set_field_property('Earning Detail', 'modified_value', 'width', '')
	p.set_field_property('Earning Detail', 'modified_value', 'trigger', 'Client')
	p.set_field_property('Deduction Detail', 'd_modified_amt', 'width', '')
	p.set_field_property('Earning Detail', 'd_modified_amt', 'trigger', 'Client')
	sql("Update tabDocField set `description` = 'You can create more earning and deduction type from Setup --> HR' where label = 'Earning & Deduction' and parent = 'Salary Structure' and fieldtype = 'Section Break'")

	# delete
	sql("update `tabSalary Structure` set net_pay = total")
	sql("delete from tabDocField where label in ('LWP Help', 'Calculate Total', 'Total') and parent = 'Salary Structure'")
	sql("delete from tabDocPerm where parent in ('Earning Detail', 'Deduction Detail')")


	# permission
	p.delete_permission('Salary Structure', 'Administrator', 0)
	p.delete_permission('Salary Structure', 'Administrator', 1)
	p.add_permission('Salary Structure', 'Employee', 0, read = 1, match = 'owner')
	p.add_permission('Salary Structure', 'Employee', 1, read = 1, match = 'owner')
elif patch_no == 77:
	# sal slip patch
	# import
	from webnotes.modules.import_module import import_from_files
	import_from_files(record_list=[['hr','doctype','salary_slip'], ['hr','doctype','ss_earning_detail'],['hr','doctype','ss_deduction_detail'], ['mapper', 'DocType Mapper', 'Salary Structure-Salary Slip']])
elif patch_no == 78:
	p = get_obj('Patch Util')
	# delete
	sql("update `tabSalary Slip` set leave_encashment_amount = encashment_amount")
	p.delete_field('Salary Slip', 'encashment_amount')
	p.delete_field('Salary Slip', 'year')
	p.delete_field('Salary Slip', 'flag')
	sql("delete from tabDocField where label = 'Process Payroll' and parent = 'Salary Slip'")

	# field property
	p.set_field_property('Salary Slip', 'bank_name', 'permlevel', '1')
	p.set_field_property('Salary Slip', 'leave_without_pay', 'permlevel', '0')
	p.set_field_property('Salary Slip', 'leave_without_pay', 'trigger', 'Client')
	p.set_field_property('SS Earning Detail', 'e_type', 'permlevel', '0')
	p.set_field_property('SS Earning Detail', 'e_type', 'fieldtype', 'Link')
	p.set_field_property('SS Earning Detail', 'e_type', 'options', 'Earning Type')
	p.set_field_property('SS Deduction Detail', 'd_type', 'permlevel', '0')
	p.set_field_property('SS Deduction Detail', 'd_type', 'fieldtype', 'Link')
	p.set_field_property('SS Deduction Detail', 'd_type', 'options', 'Deduction Type')
	sql("update `tabSS Earning Detail` set e_modified_amount = e_amount")
	sql("update `tabSS Deduction Detail` set d_modified_amount = d_amount")

	# permission
	p.delete_permission('Salary Slip', 'Administrator', 0)
	p.delete_permission('Salary Slip', 'Administrator', 1)
	p.add_permission('Salary Slip', 'Employee', 0, read = 1, match = 'owner')
	p.add_permission('Salary Slip', 'Employee', 1, read = 1, match = 'owner')
elif patch_no == 79:
	# Import Modules
	import_from_files(record_list=[['hr','doctype','leave_application'],['hr','doctype','leave_allocation'],['hr','doctype','leave_control_panel'],['hr','doctype','holiday_list'],['hr','doctype','holiday_list_detail'],['hr','Module Def','HR']])
elif patch_no == 80:
	# Holiday List
	sql("update `tabHoliday List Detail` set description = holiday_name")
	sql("delete from tabDocField where parent = 'Holiday List Detail' and fieldname = 'holiday_name'")
	sql("update tabDocField set fieldtype = 'Select', options = 'link:Fiscal Year' where parent = 'Holiday List' and fieldname = 'fiscal_year'")
	sql("delete from tabDocPerm where role in ('Administrator','HR User') and parent = 'Holiday List'")

	# Leave Control Panel
	# --------------------
	sql("delete from `tabDocField` where parent = 'Leave Control Panel' and label in ('Leave Control Panel','Allocation Details') and fieldtype = 'Section Break'")
	sql("delete from tabDocField where parent = 'Leave Control Panel' and fieldname in ('col_brk3','allocation_type','col_brk2','from_date','to_date','leave_transaction_type','posting_date')")
	sql("update tabDocField set fieldtype = 'Select', options = 'link:Fiscal Year' where parent = 'Leave Control Panel' and fieldname = 'fiscal_year'")
	sql("update tabDocField set fieldtype = 'Select', options = 'link:Leave Type' where parent = 'Leave Control Panel' and fieldname = 'leave_type'")
	sql("update tabDocField set reqd = 1 where parent = 'Leave Control Panel' and fieldname = 'no_of_days'")

	# Leave Application
	# ------------------
	for d in sql("select * from `tabLeave Transaction` where leave_transaction_type = 'Deduction' and ifnull(deduction_type, '') = 'Leave'", as_dict = 1):
		lp = Document('Leave Application')
		lp.employee = d['employee']
		lp.leave_type = d['leave_type']
		lp.posting_date = d['date']
		lp.fiscal_year = d['fiscal_year']
		lp.leave_balance = d['pre_balance']
		lp.half_day = d['half_day']
		lp.from_date = d['from_date']
		lp.to_date = d['to_date']
		lp.total_leave_days = d['total_leave']
		lp.description = d['reason']
		lp.docstatus = cint(d['docstatus'])
		lp.save(1)

	# Leave Allocation
	# -----------------
	for d in sql("select * from `tabLeave Transaction` where leave_transaction_type = 'Allocation'", as_dict = 1):
		la = Document('Leave Allocation')
		la.employee = d['employee']
		la.leave_type = d['leave_type']
		la.posting_date = d['date']
		la.fiscal_year = d['fiscal_year']
		la.new_leaves_allocated = d['total_leave']
		la.total_leaves_allocated = d['total_leave']
		la.description = d['reason']
		la.docstatus = cint(d['docstatus'])
		la.save(1)

	# Payroll Module Def
	# -------------------
	sql("delete from `tabModule Def Item` where doc_name = 'Leave Transaction' and display_name = 'Leave Transaction' and parent = 'Payroll' and doc_type = 'Forms'")

elif patch_no == 81:
	# Import Modules
	import_from_files(record_list=[['hr','Module Def','HR']])
elif patch_no == 82:
	sql("update tabDocType set search_fields = 'employee,leave_type,total_leaves_allocated,fiscal_year' where name = 'Leave Allocation'")
	sql("update tabDocType set search_fields = 'employee,leave_type,from_date,to_date,total_leave_days,fiscal_year' where name = 'Leave Application'")
elif patch_no == 83:
	# delete leave transaction
	webnotes.conn.sql("set foreign_key_checks=0")
	sql("delete from `tabLeave Transaction`")
	import webnotes.model
	webnotes.model.delete_doc('DocType','Badge Settings Detail')
	webnotes.model.delete_doc('DocType','Leave Transaction')
	webnotes.conn.sql("set foreign_key_checks=1")
elif patch_no == 84:
	p = get_obj('Patch Util')
	p.set_field_property('SS Earning Detail', 'e_amount', 'permlevel', '1')
	p.set_field_property('SS Deduction Detail', 'd_amount', 'permlevel', '1')
elif patch_no == 85:
	# permission
	p = get_obj('Patch Util')
	p.add_permission('Leave Application', 'Employee', 0, read = 1, write = 1, create = 1, submit = 1, cancel = 1, amend = 1, match = 'owner')
	p.add_permission('Leave Application', 'Employee', 1, read = 1, match = 'owner')
	p.add_permission('Leave Allocation', 'HR User', 0, read = 1, write = 1, create = 1, submit = 1, cancel = 1, amend = 1, match = 'owner')
	p.add_permission('Leave Allocation', 'HR User', 1, read = 1)
	sql("update tabDocPerm set `match` = '' where parent = 'Leave Application' and role = 'HR User'")
elif patch_no == 86:
	# Import Modules
	import_from_files(record_list=[['hr','doctype','leave_type']])
elif patch_no == 87:
	sql("update `tabLeave Type` set is_lwp = 1 where name = 'Leave Without Pay'")
elif patch_no == 88:
	# Import Modules
	import_from_files(record_list=[['hr','doctype','leave_allocation']])

elif patch_no == 89:
	sql("delete from `tabModule Def Item` where doc_type = 'Setup Forms' and doc_name in ('Payroll Rule', 'IT Checklist', 'Employee Profile') and parent = 'Payroll'")
	sql("update `tabDocField` set `hidden` = 1, `print_hide` = 1, `report_hide` = 1 where parent = 'Leave Type' and fieldname = 'is_encash'")
elif patch_no == 90:
	sql("update `tabLeave Allocation` set docstatus = 1")
elif patch_no == 91:
	import webnotes
	webnotes.conn.set_global("system_message", """<h3>System Updates</h3>Based on user feedback, we have cleaned up HR module (Partly):<ul><li>Employee and Employee Profile are merged into a single document</li><li>Salary Structure and Salary Slip are now more user friendly</li><li>Leave Transaction document is now divided into 2 documents Leave Application and Leave Allocation</li></ul>We will work on Reports, Attendance and other documents of Payroll module next week<br><br> Do send us your feedback!""")
	webnotes.conn.set_global("system_message_id", "5")
elif patch_no == 92:
	sql("update tabDocField set label = 'Get Charges' where parent IN ('Sales Order','Delivery Note','Receivable Voucher') and label = 'Get Other Charges' and fieldtype = 'Button'")
	# Automated Other Charges Calculation basis
	sql("update tabDocField set options = '', `trigger` = 'Client' where parent IN ('Quotation','Sales Order','Delivery Note','Receivable Voucher') and label = 'Get Charges' and fieldtype = 'Button'")
elif patch_no == 93:
	sql("update `tabTable Mapper Detail` set validation_logic = 'qty > ifnull(billed_qty,0) and docstatus = 1' where parent = 'Sales Order-Receivable Voucher' and from_table = 'Sales Order Detail'")
	sql("update `tabField Mapper Detail` set from_field = 'customer' where to_field = 'customer' and parent = 'Sales Order-Receivable Voucher'")
elif patch_no == 94:
	import_from_files(record_list=[['selling','doctype','sms_center']])
elif patch_no == 95:
	import_from_files(record_list=[['mapper','DocType Mapper','Sales Order-Receivable Voucher'], ['mapper','DocType Mapper','Delivery Note-Receivable Voucher']])
elif patch_no == 96:
	sql("delete from `tabModule Def Item` where doc_type = 'Reports' and display_name = 'Cenvat Credit - Input or Capital Goods' and parent = 'Accounts'")
elif patch_no == 97:
	sql("update tabFeed set doc_label = 'Feed', doc_name = name where ifnull(doc_name,'') = '' and ifnull(doc_label,'') = ''")
elif patch_no == 98:
	import_from_files(record_list=[['accounts','doctype','payable_voucher']])
elif patch_no == 99:
	import_from_files(record_list=[['accounts','doctype','account']])
elif patch_no == 100:
	p = get_obj('Patch Util')
	p.set_field_property('Account', 'level', 'hidden', '1')
	p.set_field_property('Account', 'level', 'print_hide', '1')
	p.set_field_property('Account', 'account_type', 'search_index', '0')
	p.set_field_property('TDS Detail', 'tds_category', 'width', '150px')
	p.set_field_property('TDS Detail', 'special_tds_rate_applicable', 'width', '150px')
	p.set_field_property('TDS Detail', 'special_tds_rate', 'width', '150px')
	p.set_field_property('TDS Detail', 'special_tds_limit', 'width', '150px')
elif patch_no == 101:
	# Leave Application Details and Leave Allocation Details
	sql("update tabDocField set search_index = 1, in_filter = 1 where fieldname in ('employee','leave_type','fiscal_year') and parent in ('Leave Application','Leave Allocation')")
	get_obj('DocType','Leave Application').doc.save()
	get_obj('DocType','Leave Allocation').doc.save()
elif patch_no == 102:
	# make item description field editable in production order
	sql("update tabDocField set permlevel = 0 where fieldname = 'description' and parent = 'Production Order'")
elif patch_no == 103:
	sql("update tabDocField set fieldname = '' where fieldtype = 'HTML'")
elif patch_no == 104:
	import_from_files(record_list=[['hr','search_criteria','stdsrch_00001'],['hr','search_criteria','stdsrch_00002'],['hr','search_criteria','stdsrch_00003'],['hr','Module Def','HR'],['hr','doctype','leave_application'],['hr','doctype','leave_allocation']])

elif patch_no == 105:
	# Employee Leave Balance
	sql("delete from `tabModule Def Item` where parent = 'Payroll' and doc_type = 'Reports' and display_name IN ('Employeewise Leave Transaction Details','Employeewise Balance Leave Report')")
	# Update Search Fields
	sql("update tabDocType set search_fields = 'employee,employee_name,leave_type,from_date,to_date,total_leave_days,fiscal_year' where name = 'Leave Application'")
	sql("update tabDocType set search_fields = 'employee,employee_name,leave_type,total_leaves_allocated,fiscal_year' where name = 'Leave Allocation'")
elif patch_no == 106:
	for d in sql("select name,employee,employee_name from `tabLeave Allocation`"):
		if not cstr(d[2]):
			sql("update `tabLeave Allocation` set employee_name = '%s' where name = '%s'" % (webnotes.conn.get_value('Employee',cstr(d[1]),'employee_name'), cstr(d[0])))
	for d in sql("select name,employee,employee_name from `tabLeave Application`"):
		if not cstr(d[2]):
			sql("update `tabLeave Application` set employee_name = '%s' where name = '%s'" % (webnotes.conn.get_value('Employee',cstr(d[1]),'employee_name'), cstr(d[0])))
elif patch_no == 107:
	sql("delete from `tabDocField` where fieldname = 'fiscal_year' and parent = 'Employee'")
elif patch_no == 108:
	import_from_files(record_list=[['hr','search_criteria','srch_std_00013']])
elif patch_no == 109:
	import_from_files(record_list=[['hr','search_criteria','srch_std_00015']])
elif patch_no == 110:
	import_from_files(record_list=[['hr','doctype','salary_structure'], ['hr', 'doctype', 'salary_slip']])
elif patch_no == 111:
	sql("update tabDocType set search_fields = 'transfer_date, from_warehouse, to_warehouse, purpose, remarks' where name = 'Stock Entry'")
elif patch_no == 112:
	sql("delete from tabDocField where label = 'Get Other Charges' and fieldtype = 'Button' and parent = 'Receivable Voucher'")
elif patch_no == 113:
	sql("update tabDocField set reqd = 1 where parent = 'Customer' and fieldname = 'phone_1'")
elif patch_no == 114:
	for d in sql("select name, master_name, credit_days, credit_limit from tabAccount where master_type = 'Customer'"):
		if cstr(d[1]):
			days, limit = cint(d[2]), flt(d[3])
			cust_det = sql("select credit_days, credit_limit from tabCustomer where name = '%s'" % (cstr(d[1])))
			if not days: days = cust_det and cint(cust_det[0][0]) or 0
			if not limit: limit = cust_det and flt(cust_det[0][1]) or 0
			sql("COMMIT")
			sql("START TRANSACTION")
			sql("update tabAccount set credit_days = '%s', credit_limit = '%s' where name = '%s'" % (days, limit, cstr(d[0])))
			sql("COMMIT")

elif patch_no == 115:
	# patch for timesheet cleanup
	from webnotes.model import delete_doc
	delete_doc('DocType', 'Timesheet Detail')

	from webnotes.modules.import_module import import_from_files
	import_from_files(record_list = [['Projects', 'DocType', 'Timesheet'], ['Projects', 'DocType', 'Timesheet Detail'], ['Projects', 'DocType', 'Activity Type']])

elif patch_no == 116:
	# again!
	from webnotes.model import delete_doc
	delete_doc('DocType', 'Timesheet Detail')

	from webnotes.modules.import_module import import_from_files
	import_from_files(record_list = [['Projects', 'DocType', 'Timesheet Detail']])
elif patch_no == 117:
	op = '\n' + 'Walk In'
	sql("update `tabDocField` set `options` = concat(options, %s) where parent = 'Enquiry' and fieldname = 'source' and options not like '%%Walk%%'", op)
elif patch_no == 118:
	from webnotes.utils import get_defaults
	ss = sql("select name, net_pay from `tabSalary Slip`")
	for d in ss:
		if d[1]:
			w = get_obj('Sales Common').get_total_in_words(get_defaults()['currency'], d[1])
			sql("update `tabSalary Slip` set net_pay_in_words = '%s' where name = '%s'" % (w, d[0]))
elif patch_no == 119:
	sql("update tabDocType set in_create = 1 where name = 'Profile'")
elif patch_no == 120:
	sql("update tabDocField set permlevel = 0 where parent = 'Sales and Purchase Return Wizard' and fieldname = 'return_date'")
elif patch_no == 121:
	import_from_files(record_list = [['CRM', 'DocType', 'Return Detail'], ['Material Management', 'DocType', 'Sales and Purchase Return Wizard']])
elif patch_no == 122:
	sql("delete from tabDocField where (fieldname = 'serial_no' or label = 'Warrany Status') and parent = 'Sales Order'")
elif patch_no == 123:
	import_from_files(record_list = [['CRM', 'Module Def', 'CRM'], ['CRM', 'Search Criteria', 'STDSRCH/00004']])
elif patch_no == 124:
	import webnotes
	webnotes.conn.set_global("system_message", """<h3>Updates(New)</h3>We have added a new report in the Selling Module.<br><br><b>Sales Personwise Transaction Summary: </b>In this report you can see sales person's contribution in a particular order, delivery or invoice. You can select voucher type in "Based On" filter.<br><br> Do send us your feedback!""")
	webnotes.conn.set_global("system_message_id", "5")
elif patch_no == 125:
	import_from_files(record_list = [['Material Management', 'DocType', 'Delivery Note']])
elif patch_no == 126:
	sql("delete from tabDocField where parent = 'Delivery Note' and label in ('Make Sales Invoice', 'Make Installation Note', 'Intro Note')")
elif patch_no == 127:
	sql("delete from tabDocPerm where role = 'All' and parent = 'Expense Voucher' and (permlevel = 0 or permlevel = 2)")
	p = get_obj('Patch Util')
	p.add_permission('Expense Voucher', 'Employee', 0, read = 1, write = 1, create = 1, submit = 1, cancel = 1, amend = 1, match = 'owner')
	p.add_permission('Expense Voucher', 'HR Manager', 0, read = 1, write = 1, create = 1, submit = 1, cancel = 1, amend = 1)
	p.add_permission('Expense Voucher', 'HR User', 0, read = 1, write = 1, create = 1, submit = 1, cancel = 1, amend = 1)
elif patch_no == 128:
	from webnotes.modules import import_module
	import_module.import_from_files(record_list=[['selling','doctype','sales_order'], ['selling','doctype','sales_order_detail'],  ['stock','doctype','delivery_note'], ['stock','doctype','delivery_note_detail']])
elif patch_no == 129:
	sql("update `tabTable Mapper Detail` set validation_logic = '(qty > ifnull(billed_qty, 0) or amount > ifnull(billed_amt, 0)) and docstatus = 1' where parent = 'Sales Order-Receivable Voucher' and from_table = 'Sales Order Detail' and to_table = 'RV Detail'")
	sql("update `tabTable Mapper Detail` set validation_logic = '(qty > ifnull(billed_qty, 0) or amount > ifnull(billed_amt, 0)) and docstatus = 1' where parent = 'Delivery Note-Receivable Voucher' and from_table = 'Delivery Note Detail' and to_table = 'RV Detail'")
elif patch_no == 130:
	# update from rv
	from webnotes.model.code import get_obj
	from webnotes.utils import cstr
	for d in sql("select name, docstatus from `tabReceivable Voucher` where ifnull(docstatus,0) != 0"):
		sql("COMMIT")
		sql("START TRANSACTION")
		try:
			obj = get_obj('Receivable Voucher', cstr(d[0]), with_children = 1)
			is_submit = 1
			if cint(d[1]) == 2: is_submit = 0
			get_obj('Sales Common').update_prevdoc_detail(is_submit, obj)
		except:
			pass
		sql("COMMIT")

	# update from dn
	from webnotes.model.code import get_obj
	for d in sql("select name, docstatus from `tabDelivery Note` where ifnull(docstatus,0) != 0"):
		sql("COMMIT")
		sql("START TRANSACTION")
		try:
			obj = get_obj('Delivery Note', cstr(d[0]), with_children = 1)
			is_submit = 1
			if cint(d[1]) == 2: is_submit = 0
			get_obj('Sales Common').update_prevdoc_detail(is_submit, obj)
		except:
			pass
		sql("COMMIT")
elif patch_no == 131:
	sql("update `tabDocType` set allow_trash = 1 where name = 'Purchase Other Charges'")
	sql("update tabDocPerm set `cancel` = 1 where parent = 'Purchase Other Charges' and permlevel = 0 and `read` = 1 and `write` = 1")
elif patch_no == 132:
	sql("update tabDocField set no_copy = 0 where parent = 'Receivable Voucher' and fieldname = 'customer'")
elif patch_no == 133:
	from webnotes.modules import import_module
	import_module.import_from_files(record_list=[['accounts','doctype','receivable_voucher']])
elif patch_no == 134:
	sql("update tabDocField set no_copy = 1 where parent = 'Receivable Voucher' and fieldname = 'posting_time'")
elif patch_no == 135:
	sql("update tabDocField set `default` = 'Today' where parent = 'Receivable Voucher' and fieldname = 'due_date'")
elif patch_no == 136:
	from webnotes.modules import import_module
	import_module.import_from_files(record_list=[['accounts','doctype','rv_detail']])
elif patch_no == 137:
	from webnotes.modules import import_module
	import_module.import_from_files(record_list=[['setup','doctype','price_list']])
elif patch_no == 138:
	sql("update `tabDocType` set allow_attach = 1 where name = 'Price List'")
elif patch_no == 139:
	from webnotes.modules import import_module
	import_module.import_from_files(record_list=[['mapper','DocType Mapper','Sales Order-Receivable Voucher'], ['mapper','DocType Mapper','Delivery Note-Receivable Voucher']])
elif patch_no == 140:
	from webnotes.modules import import_module
	import_module.import_from_files(record_list=[['accounts','doctype','rv_detail']])
elif patch_no == 141:
	sql("delete from tabDocField where (fieldname = 'letter_head' or label = 'Letter Head') and parent = 'Company'")
elif patch_no == 142:
	# fixes to letter head and personalize
	from webnotes.model import delete_doc

	delete_doc('DocType', 'Batch Settings')
	delete_doc('DocType', 'Batch Settings Detail')
	delete_doc('DocType', 'Social Badge')
	delete_doc('Page', 'Personalize Page')
	delete_doc('DocType', 'Personalize Page Control')

	import_from_files(record_list=[['core','doctype','letter_head'], ['setup','doctype','personalize']])
elif patch_no == 144:
	webnotes.conn.sql("update tabDocField set fieldtype='Code' where parent='Letter Head' and fieldname='content'")
elif patch_no == 145:
	sql("update `tabDocField` set permlevel=1 where fieldname = 'group_or_ledger' and parent = 'Account'")
elif patch_no == 146:
	import_from_files(record_list=[['accounts','doctype','account']])
elif patch_no == 147:
	import_from_files(record_list=[['mapper', 'DocType Mapper', 'Purchase Order-Payable Voucher'], ['mapper', 'DocType Mapper', 'Purchase Receipt-Payable Voucher'], ['mapper', 'DocType Mapper', 'Purchase Order-Purchase Receipt']])
elif patch_no == 148:
	sql("delete from `tabDocField` where (fieldname = 'account_balances' or label = 'Balances') and parent = 'Account'")
	sql("update tabDocType set istable = 0, section_style = 'Simple', search_fields = 'account, period, fiscal_year, balance' where name = 'Account Balance'")
	sql("update tabDocField set permlevel = 0 where parent = 'Account Balance'")
	p = get_obj('Patch Util')
	p.add_permission('Account Balance', 'Accounts User', 0, read = 1)
	p.add_permission('Account Balance', 'Accounts Manager', 0, read = 1)
	import_from_files(record_list=[['accounts','doctype','account_balance']])
elif patch_no == 149:
	sql("update `tabAccount Balance` set account = parent")
elif patch_no == 150:
	sql("update tabDocField set in_filter = 1, search_index = 1 where parent = 'Account Balance' and fieldname in ('account', 'period', 'fiscal_year', 'start_date', 'end_date')")
	ac_bal = Document("DocType", "Account Balance")
	ac_bal.save()
elif patch_no == 151:
	sql("delete from tabDocField where label = 'Add / Manage Contacts' and fieldtype = 'Button' and parent = 'Customer'")
	sql("delete from `tabField Mapper Detail` where parent = 'Sales Order-Delivery Note' and from_field = 'note' and to_field = 'note'")
elif patch_no == 152:
	import_from_files(record_list=[['selling','doctype','sales_order'], ['stock','doctype','delivery_note'], ['selling','doctype','customer'], ['selling','doctype','shipping_address'], ['mapper', 'DocType Mapper', 'Sales Order-Delivery Note']])
elif patch_no == 153:
	sql("delete from `tabDocField` where fieldname = 'sales_person' and parent = 'Customer'")
elif patch_no == 154:
	import_from_files(record_list=[['stock','doctype','serial_no'], ['support','doctype','customer_issue']])
elif patch_no == 155:
	for d in sql("select name, item_code from `tabSerial No`"):
		sql("COMMIT")
		sql("START TRANSACTION")
		sql("update `tabSerial No` set item_name = '%s' where name = '%s'" % (webnotes.conn.get_value('Item',cstr(d[1]),'item_name'), cstr(d[0])))
		sql("COMMIT")
elif patch_no == 156:
	sql("update tabDocField set fieldtype = 'Code' where fieldname = 'html' and parent = 'Print Format'")
elif patch_no == 157:
	import_from_files(record_list=[['accounts', 'doctype', 'journal_voucher'], ['accounts', 'Print Format', 'Payment Receipt Voucher'], ['accounts', 'Print Format', 'Cheque Printing Format']])
elif patch_no == 158:
	from webnotes.model.doc import addchild
	sql("delete from tabDocField where parent = 'Customer Issue' and fieldname = 'customer_group'")
elif patch_no == 159:
	sql("update tabAccount set account_type = 'Chargeable' where account_name in ('Advertising and Publicity', 'Freight & Forwarding Charges', 'Miscellaneous Expenses', 'Sales Promotion Expenses')")
elif patch_no == 160:
	sql("update `tabDocType` set search_fields = 'posting_date, due_date, debit_to, fiscal_year, grand_total, outstanding_amount' where name = 'Receivable Voucher'")
	sql("update `tabDocType` set search_fields = 'posting_date, credit_to, fiscal_year, bill_no, grand_total, outstanding_amount' where name = 'Payable Voucher'")
elif patch_no == 161:
	sql("update tabDocType set autoname = 'field:batch_id' where name = 'Batch'")
	sql("update tabDocField set no_copy = 1 where parent = 'Batch' and fieldname = 'batch_id'")
elif patch_no == 162:
	import_from_files(record_list=[['selling', 'search_criteria', 'sales_order_pending_items1']])
elif patch_no == 163:
	sql("delete from `tabModule Def Item` where display_name = 'Sales Orderwise Pending Packing Item Summary' and parent = 'CRM'")
	import_from_files(record_list=[['selling', 'search_criteria', 'sales_orderwise_pending_qty_to_deliver'], ['selling', 'search_criteria', 'sales_orderwise_pending_amount_to_bill'], ['selling', 'search_criteria', 'delivered_items_to_be_install']])
elif patch_no == 164:
	import_from_files(record_list=[['buying', 'search_criteria', 'pending_po_items_to_receive'], ['buying', 'search_criteria', 'pending_po_items_to_bill']])
elif patch_no == 165:
	pass
elif patch_no == 166:
	import_from_files(record_list=[['buying', 'doctype', 'purchase_order']])
elif patch_no == 167:
	if webnotes.conn.get_value('Control Panel', None, 'account_id') not in ['ax0000956', 'ax0001338']:
		sql("delete from tabDocField where parent = 'Purchase Order' and fieldname in ('test_certificate_required', 'estimated_cost', 'transport', 'vendor_reference', 'transportation_required', 'mode_of_dispatch', 'octroi')")
elif patch_no == 168:
	sql("update tabDocField set fieldtype = 'Data', options = 'Suggest' where fieldname = 'bank_name' and parent = 'Employee'")
elif patch_no == 169:
	import_from_files(record_list=[['accounts', 'doctype', 'pv_detail'], ['accounts', 'doctype', 'rv_detail']])
elif patch_no == 170:
	import_from_files(record_list=[['mapper', 'DocType Mapper', 'Delivery Note-Receivable Voucher']])
elif patch_no == 171:
	import_from_files(record_list=[['buying', 'doctype', 'supplier']])
elif patch_no == 172:
	import webnotes
	webnotes.conn.set_global("system_message", """<b>Welcome to the new financial year 2011-2012 !!! </b><br><br> So obvious question in your mind is how to start Entries in the New Fiscal Year in ERPNext? What are the changes you have to make in the system? <br>We have made some guidelines regarding the basic steps you should follow. Please click on link <a href='http://erpnext.blogspot.com/2011/03/how-to-start-entries-in-new-fiscal-year.html'>How to start Entries in the New Fiscal Year in ERPNext?</a>""")
	webnotes.conn.set_global("system_message_id", "6")
elif patch_no == 173:
	sql("delete from tabDocField where label = 'Get Other Charges' and parent = 'Delivery Note'")
	sql("update tabDocField set reqd = 0 where fieldname = 'posting_time' and parent = 'Serial No'")
elif patch_no == 174:
	c = sql("select count(name) from `tabField Mapper Detail` where parent = 'Delivery Note-Receivable Voucher' and from_field = 'description' and to_field = 'description' and match_id = 2")
	if c and cint(c[0][0]) > 1:
		sql("update `tabField Mapper Detail` set match_id = 1 where parent = 'Delivery Note-Receivable Voucher' and from_field = 'description' and to_field = 'description' limit 1")
elif patch_no == 175:
	import webnotes
	webnotes.conn.set_global("system_message", """If your financial year starts on 1st April then you have make some changes in the system to start entry in the new year.<br>We have made some guidelines regarding the basic steps you should follow. Please click on link <a href='http://erpnext.blogspot.com/2011/03/how-to-start-entries-in-new-fiscal-year.html'>How to start Entries in the New Fiscal Year in ERPNext?</a>""")
	webnotes.conn.set_global("system_message_id", "6")
elif patch_no == 176:
	sql("update tabDocPerm set role='Guest', `write`=0, `create`=0 where role='Administrator' and parent='Notification Control' limit 1")
elif patch_no == 177:
	sql("delete from `tabDocField` where label = 'Next Steps' and parent = 'Purchase Order'")
	sql("update tabDocField set options = 'Material Issue\nMaterial Receipt\nMaterial Transfer\nSales Return\nPurchase Return\nSubcontracting\nProduction Order' where parent = 'Stock Entry' and fieldname = 'purpose'")
elif patch_no == 178:
	import_from_files(record_list = [['hr', 'doctype', 'salary_slip']])
elif patch_no == 179:
	from webnotes.utils import get_defaults
	sl = sql("select name, net_pay from `tabSalary Slip`")
	for d in sl:
		in_words = get_obj('Sales Common').get_total_in_words(get_defaults()['currency'], round(flt(d[1])))
		sql("update `tabSalary Slip` set rounded_total = '%s', total_in_words = '%s' where name = '%s'" % (round(flt(d[1])), in_words, d[0]))
elif patch_no == 180:
	sql("delete from tabDocField where parent = 'Salary Slip' and fieldname = 'net_pay_in_words'")
elif patch_no == 181:
	import_from_files(record_list = [['accounts', 'doctype', 'journal_voucher']])
elif patch_no == 182:
	sql("update tabDocField set options = CONCAT(options, '\nWrite Off Voucher') where fieldname = 'voucher_type' and parent = 'Journal Voucher'")
elif patch_no == 183:
	sql("delete from tabDocField where label = 'SMS' and fieldtype = 'Section Break' and parent in  ('Enquiry', 'Lead', 'Sales Order', 'Delivery Note')")
elif patch_no == 184:
	from webnotes.model import delete_doc
	delete_doc('DocType', 'Feed')
	delete_doc('DocType', 'Feed List')
	delete_doc('DocType', 'Feed Control')

	# add trigger
	from webnotes.model.triggers import add_trigger
	add_trigger('*','*','*','event_updates.update_feed')

	webnotes.conn.commit()

	try:
		sql("drop table tabFeed")
		sql("drop table `tabFeed List`")
	except: pass

	# import
	from webnotes.modules.module_manager import reload_doc
	reload_doc('event_updates','doctype','feed')
elif patch_no==185:
	sql("delete from tabDocTrigger where method = 'webnotes.widgets.follow.on_docsave'")
elif patch_no==186:
	from webnotes.modules.module_manager import reload_doc
	reload_doc('event_updates','doctype','feed')
elif patch_no == 187:
	sql("update tabDocType set autoname = '' where name = 'QA Inspection Report'")
elif patch_no == 188:
	import_from_files(record_list = [['buying', 'doctype', 'qa_inspection_report']])
elif patch_no == 189:
	sql("update `tabDocField` set allow_on_submit = 1 where fieldname in ('entries', 'other_charges') and parent = 'Receivable Voucher'")
elif patch_no == 190:
	sql("update tabDocField set permlevel=0 where fieldname = 'fiscal_year' and parent = 'Stock Entry'")
elif patch_no == 191:
	import_from_files(record_list = [['support', 'doctype', 'customer_issue']])
elif patch_no == 192:
	sql("delete from `tabModule Def Item` where parent = 'Material Management' and doc_name = 'Landed Cost Wizard' and display_name = 'Landed Cost Wizard'")
	import_from_files(record_list = [['buying', 'Module Def', 'SRM']])
elif patch_no == 193:
	sql("update tabDocField set fieldtype='Button', `trigger`='Client' where parent='Letter Head' and fieldname='set_from_image'")
elif patch_no == 194:
	sql("delete from `tabModule Def Item` where parent = 'SRM' and doc_name = 'Landed Cost Wizard' and display_name = 'Landed Cost Wizard'")
	import_from_files(record_list = [['stock', 'Module Def', 'Material Management']])
elif patch_no == 195:
	from webnotes.modules.module_manager import reload_doc
	reload_doc('setup','doctype','manage_account')
elif patch_no == 196:
	sql("update `tabModule Def` set module_page = null where name = 'Material Management'")
elif patch_no == 197:
	sql("update `tabDocField` set permlevel = 0, in_filter = 1 where fieldname = 'warranty_amc_status' and parent = 'Customer Issue'")
	import_from_files(record_list = [['support', 'doctype', 'customer_issue']])
elif patch_no == 198:
	sql("delete from `tabDocField` where (label in ('SMS', 'Send SMS') or fieldname in ('message', 'customer_mobile_no')) and parent in ('Quoattion', 'Sales Order', 'Delivery Note', 'Receivable Voucher')")
	sql("delete from `tabDocField` where label in ('SMS', 'Send SMS') and parent = 'Purchase Order'")
	sql("delete from `tabDocField` where (label in ('Send SMS', 'SMS Html') or fieldname in ('sms_message', 'lead_sms_detail', 'enquiry_sms_detail')) and parent in ('Lead', 'Enquiry')")
	from webnotes.model import delete_doc
	delete_doc('DocType', 'Lead SMS Detail')
	delete_doc('DocType', 'Enquiry SMS Detail')
elif patch_no == 199:
	sql("update tabDocField set reqd = 0 where parent = 'Attendance' and fieldname = 'shifts'")
elif patch_no == 200:
	reload_doc('event_updates','page','profile_settings')
elif patch_no == 201:
	reload_doc('setup','doctype','price_list')
elif patch_no == 202:
	name1 = sql("select name from tabDocField where parent='Price List' and label='Clear Prices' limit 1,1")
	name2 = sql("select name from tabDocField where parent='Price List' and label='Update Prices' limit 1,1")
	if name1:
		sql("delete from tabDocField where name=%s limit 1", name1[0][0])
	if name2:
		sql("delete from tabDocField where name=%s limit 1", name2[0][0])
elif patch_no == 203:
	sql("delete from tabDocField where parent = 'Company' and fieldname = 'default_salary_account' limit 1")
elif patch_no == 204:
	sql("delete from tabDocField where parent = 'Company' and fieldname = 'default_salary_acount' limit 1")
elif patch_no == 205:
	sql("update `tabDocField` set `default` = '' where fieldname = 'naming_series' and parent = 'Installation Note'")
elif patch_no == 206:
	reload_doc('selling','doctype','installation_note')
elif patch_no == 207:
	import_from_files(record_list = [['setup', 'doctype', 'company']])
elif patch_no == 208:
	sql("delete from `tabDocField` where (label in ('SMS', 'Send SMS') or fieldname in ('message', 'customer_mobile_no')) and parent ='Quotation'")
	default_currency = get_obj('Manage Account').doc.default_currency
	sql("update tabCompany set default_currency = '%s'" % default_currency)
elif patch_no == 209:
	import_from_files(record_list = [['setup', 'doctype', 'company']])
elif patch_no == 210:
	sql("delete FROM `tabDocField` WHERE parent = 'Lead' AND label in ('CC:','Attachment Html','Create New File','Attachment')")
elif patch_no == 212:
	# reload company because of disturbed UI
	import_from_files(record_list = [['setup', 'doctype', 'company']])
elif patch_no == 213:
	reload_doc('selling','doctype','lead')
	reload_doc('setup','doctype','company')
elif patch_no == 214:
	reload_doc('selling','doctype','sales_order')
elif patch_no == 215:
	# patch for item and image in description
	sql("update tabDocField set width = '300px' where fieldname='description'")
	reload_doc('stock', 'doctype', 'item')
	sql("delete from __DocTypeCache")
elif patch_no == 216:
	import_from_files(record_list = [['stock', 'doctype', 'serial_no'], ['stock', 'doctype', 'stock_ledger_entry']])
elif patch_no == 217:
	sql("update tabDocField set options = '\nIn Store\nDelivered\nNot in Use' where fieldname = 'status' and parent = 'Serial No'")
	sql("update tabDocField set no_copy = 1 where fieldname = 'serial_no' and parent = 'Delivery Note Detail'")
	sql("update tabDocField set no_copy = 1 where fieldname = 'serial_no' and parent = 'Stock Entry Detail'")
elif patch_no == 218:
	for d in sql("select name from `tabSerial No`"):
		sql("Commit")
		sql("Start Transaction")
		s = Document('Serial No', d[0])
		if s.pr_no:
			s.purchase_document_type = 'Purchase Receipt'
			s.purchase_document_no = s.pr_no
		if s.delivery_note_no:
			s.delivery_document_type = 'Delivery Note'
			s.delivery_document_no = s.delivery_note_no
		if s.notes:
			s.delivery_note_no = s.notes
		s.company = webnotes.utils.get_defaults()['company']
		s.fiscal_year = webnotes.utils.get_defaults()['fiscal_year']
		s.save()
elif patch_no == 219:
	sql("delete from tabDocField where fieldname in ('pr_no', 'make', 'label', 'delivery_note_no', 'notes') and parent = 'Serial No'")
elif patch_no == 220:
	sql("update tabDocField set label = 'Incoming Rate' where fieldname = 'purchase_rate' and parent = 'Serial No'")
	sql("update tabDocField set label = 'Incoming Time' where fieldname = 'purchase_time' and parent = 'Serial No'")
elif patch_no == 221:
	sql("update tabDocField set reqd = 1 where fieldname in ('purchase_rate', 'warehouse') and parent = 'Serial No'")
elif patch_no == 222:
	sql("update tabDocField set options = '\nDelivery Note\nReceivable Voucher\nStock Entry' where fieldname = 'delivery_document_type' and parent = 'Serial No'")
elif patch_no == 223:
	sql("update tabDocField set hidden = 0 where fieldname in ('pay_to_recd_from', 'total_amount', 'total_amount_in_words') and parent = 'Journal Voucher'")
	sql("update tabDocField set permlevel = 0 where fieldname = 'pay_to_recd_from' and parent = 'Journal Voucher'")
elif patch_no == 224:
	import_from_files(record_list = [['stock', 'doctype', 'delivery_note_packing_detail'], ['accounts', 'Print Format', 'Payment Receipt Voucher']])
elif patch_no == 225:
	import_from_files(record_list = [['stock', 'doctype', 'delivery_note_packing_detail']])
elif patch_no == 226:
	import_from_files(record_list = [['stock', 'doctype', 'delivery_note_packing_detail']])
elif patch_no == 227:
	reload_doc('stock', 'doctype', 'item')
	if webnotes.conn.get_value('Control Panel', None, 'account_id') != 'axjanak2011':
		sql("delete from tabDocField where parent = 'Item' and fieldname='alternate_description' limit 1")
elif patch_no == 228:
	# knowledge base patch
	reload_doc('knowledge_base', 'doctype', 'question')
	reload_doc('knowledge_base', 'doctype', 'answer')
	reload_doc('knowledge_base', 'page', 'questions')
	reload_doc('knowledge_base', 'Module Def', 'Knowledge Base')
	sql("update `tabModule Def` set disabled='No' where name='Knowledge Base'")
elif patch_no == 229:
	reload_doc('knowledge_base', 'page', 'question_view')
elif patch_no == 230:
	reload_doc('buying', 'doctype', 'indent')
	reload_doc('buying', 'doctype', 'indent_detail')
	reload_doc('Mapper', 'DocType Mapper', 'Sales Order-Indent')
elif patch_no == 231:
	reload_doc('Mapper', 'DocType Mapper', 'Sales Order-Indent')
elif patch_no == 232:
	sql("update `tabDocField` set options = 'Sales Order' where fieldname = 'sales_order_no' and parent = 'Indent'")
elif patch_no == 233:
	reload_doc('Mapper', 'DocType Mapper', 'Sales Order-Receivable Voucher')
	reload_doc('Mapper', 'DocType Mapper', 'Delivery Note-Receivable Voucher')
elif patch_no == 234:
	sql("update `tabTable Mapper Detail` set validation_logic = 'docstatus=1' where parent = 'Sales Order-Indent' and from_table = 'Sales Order Detail'")
elif patch_no == 235:
	for sc in sql("""select name from `tabSearch Criteria` where ifnull(name,'')
		like 'srch%' or ifnull(name,'') like '%stdsrch'"""):
		try:
			get_obj('Search Criteria', sc[0]).rename()
		except AttributeError, e:
			pass
	reload_doc('core', 'doctype', 'system_console')
elif patch_no == 236:
	# warehouse not mandatory for delivered serial nos
	sql("update tabDocField set reqd=0 where parent='Serial No' and fieldname='warehouse'")
elif patch_no == 237:
	sql("update tabDocField set depends_on = 'eval:doc.is_pos==1' where fieldname = 'cash_bank_account' and parent = 'Receivable Voucher'")
elif patch_no == 238:
	reload_doc('accounts', 'doctype', 'receivable_voucher')
	reload_doc('accounts', 'GL Mapper', 'POS with write off')
elif patch_no == 239:
	reload_doc('core', 'doctype', 'docfield')
	reload_doc('core', 'doctype', 'doctype')
	from patches.old_patches.feed_patch import set_subjects_and_tagfields

	set_subjects_and_tagfields()
elif patch_no == 240:
	# again for sales order (status)
	from patches.old_patches.feed_patch import set_subjects_and_tagfields
	set_subjects_and_tagfields()
elif patch_no == 241:
	sql("update `tabDocField` set fieldtype = 'Text', options = '', in_filter = '' where fieldname = 'serial_no' and parent = 'Stock Ledger Entry'")
elif patch_no == 242:
	if webnotes.conn.get_value('Control Panel', None, 'account_id') not in ['axjanak2011']:
		sql("commit")
		try:
			sql("alter table `tabStock Ledger Entry` drop index serial_no")
		except:
			pass

		sql("alter table `tabStock Ledger Entry` change serial_no serial_no text")
elif patch_no == 243:
	# moving custom script and custom fields to framework
	webnotes.conn.set_value('DocType', 'Custom Script', 'module', 'Core')
	webnotes.conn.set_value('DocType', 'Custom Field', 'module', 'Core')
	reload_doc('setup', 'doctype', 'company')
elif patch_no == 244:
	reload_doc('stock', 'search_criteria', 'shortage_to_indent')
elif patch_no == 245:
	from patches.old_patches.doctype_permission_patch import set_doctype_permissions
	set_doctype_permissions()

	from patches.old_patches.feed_patch import set_subjects_and_tagfields
	set_subjects_and_tagfields()
elif patch_no == 246:
	webnotes.conn.set_value('DocType','Stock Entry','tag_fields','purpose')
	webnotes.conn.set_value('DocType','Stock Entry','subject','%(remarks)s')
elif patch_no == 247:
	webnotes.conn.set_value('DocType','Stock Entry','subject','%(remarks)s')
elif patch_no == 248:
	reload_doc('setup', 'doctype', 'manage_account')
elif patch_no == 249:
	sql("update `tabDocPerm` t1, `tabDocType` t2 set t1.role = 'System Manager' where t1.role = 'Administrator' and t1.parent = t2.name and t2.module != 'Core'")
elif patch_no == 250:
	from patches.old_patches.feed_patch  import support_patch
	support_patch()
elif patch_no == 251:
	from webnotes.model import db_schema
	db_schema.remove_all_foreign_keys()
	from patches.old_patches.customer_address import run_patch
	run_patch()
elif patch_no == 252:
	reload_doc('support','doctype','support_ticket')
	reload_doc('support','doctype','support_ticket_response')
elif patch_no == 253:
	reload_doc('accounts','doctype','ledger_balance_export')
	reload_doc('accounts','doctype','ledger_detail')
	reload_doc('accounts', 'Module Def', 'Accounts')

	from webnotes.model.db_schema import updatedb
	updatedb('Ledger Balance Export')
	updatedb('Ledger Detail')
elif patch_no == 254:
	reload_doc('setup', 'doctype', 'sms_settings')
	reload_doc('setup', 'doctype', 'static_parameter_detail')

	from webnotes.model.db_schema import updatedb
	updatedb('SMS Settings')
	updatedb('Static Parameter Detail')
elif patch_no == 255:
	from patches.old_patches.customer_address import run_old_data_sync_patch
	run_old_data_sync_patch()
elif patch_no == 256:
	sql("update `tabLetter Head` set content = replace(content, 'http://46.4.50.84/v170-test/', '')")
	sql("update `tabSingles` set value = replace(value, 'http://46.4.50.84/v170-test/', '') where field in ('letter_head', 'client_name') and doctype = 'Control Panel'")
	sql("update `tabItem` set description_html = replace(description_html, 'http://46.4.50.84/v170-test/', '')")
elif patch_no == 257:
	from patches.old_patches.customer_address import run_old_data_sync_patch
	run_old_data_sync_patch()
elif patch_no == 258:
	sql("update tabDocField set `default`=NULL where fieldname = 'naming_series'")
elif patch_no == 259:
	sql("update `tabQuotation Detail` set description = replace(description, 'http://46.4.50.84/v170-test/', '')")
	sql("update `tabSales Order Detail` set description = replace(description, 'http://46.4.50.84/v170-test/', '')")
	sql("update `tabRV Detail` set description = replace(description, 'http://46.4.50.84/v170-test/', '')")
	sql("update `tabDelivery Note Detail` set description = replace(description, 'http://46.4.50.84/v170-test/', '')")
elif patch_no == 260:
	sql("update `tabLetter Head` set content = replace(content, 'http://46.4.50.84/v170/', '')")
	sql("update `tabSingles` set value = replace(value, 'http://46.4.50.84/v170/', '') where field in ('letter_head', 'client_name') and doctype = 'Control Panel'")
	sql("update `tabItem` set description_html = replace(description_html, 'http://46.4.50.84/v170/', '')")
	sql("update `tabQuotation Detail` set description = replace(description, 'http://46.4.50.84/v170/', '')")
	sql("update `tabSales Order Detail` set description = replace(description, 'http://46.4.50.84/v170/', '')")
	sql("update `tabRV Detail` set description = replace(description, 'http://46.4.50.84/v170/', '')")
	sql("update `tabDelivery Note Detail` set description = replace(description, 'http://46.4.50.84/v170/', '')")
elif patch_no == 261:
	sql("update `tabPrint Format` set html = replace(html, 'customer_address', 'address_display')")
elif patch_no == 262:
	from patches.old_patches.customer_address import sync_lead_phone
	sync_lead_phone()
elif patch_no == 263:
	ol = ['','Open','To Reply','Waiting for Customer','Hold','Closed']
	sql("update tabDocField set options=%s where parent=%s and fieldname=%s", ('\n'.join(ol), 'Support Ticket', 'status'))
elif patch_no == 264:
	sql("delete from tabDocField where parent = 'Customer Issue' and (fieldname = 'issue_in' or fieldname = 'issue_category')")
	sql("update tabDocField set options=NULL where parent='Support Ticket' and label = 'Send'")
elif patch_no == 266:
	reload_doc('setup','doctype','support_email_settings')
elif patch_no == 267:
	sql("update `tabPrint Format` set html = replace(html, 'supplier_address', 'address_display')")
elif patch_no == 268:
	sql("update `tabDocPerm` set permlevel = 0 where permlevel is null")
elif patch_no == 269:
	p = get_obj('Patch Util')
	p.add_permission('GL Entry', 'Accounts User', 0, read = 1)
elif patch_no == 270:
	pages = ['Accounts Setup', 'Accounts', 'Accounting Reports','GeneralLedger','How do I - Accounts','Making Opening Entries',\
	'Analysis','How do I - CRM','How do I - Inventory','Inventory Setup', 'Stock','HR','HR & Payroll Setup',\
	'Payroll Setup','Production Setup','Production','Buying','SRM Setup','Contact Page','Forum','Messages','Test Toolbar',\
	'Trend Analyzer']
	from webnotes.model import delete_doc
	sql("delete from `tabPage Visit`")
	for p in pages:
		try: delete_doc('Page', p)
		except: pass
elif patch_no == 271:
	# tags patch
	reload_doc('selling','doctype','sales_order')
	reload_doc('stock','doctype','delivery_note')
	sql("delete from tabDocField where fieldname='per_amt_billed' and parent in ('Sales Order', 'Delivery Note')")

	sql("""update `tabSales Order` set delivery_status = if(ifnull(per_delivered,0) < 0.001, 'Not Delivered',
			if(per_delivered >= 99.99, 'Fully Delivered', 'Partly Delivered'))""")
	sql("""update `tabSales Order` set billing_status = if(ifnull(per_billed,0) < 0.001, 'Not Billed',
			if(per_billed >= 99.99, 'Fully Billed', 'Partly Billed'))""")
	sql("""update `tabDelivery Note` set billing_status = if(ifnull(per_billed,0) < 0.001, 'Not Billed',
			if(per_billed >= 99.99, 'Fully Billed', 'Partly Billed'))""")
elif patch_no == 272:
	from webnotes.model import delete_doc
	try:
		delete_doc('Search Criteria', '_SRCH00003')
	except:
		pass
	reload_doc('accounts', 'search_criteria', 'purchase_register')
elif patch_no == 276:
	from webnotes.model import delete_doc
	sn = sql("select name from `tabSearch Criteria` where criteria_name = 'Sales Personwise Transaction Summary'")
	for d in sn:
		delete_doc('Search Criteria', d[0])
	reload_doc('selling', 'search_criteria', 'sales_personwise_transaction_summary')
elif patch_no == 277:
	webnotes.model.delete_doc('DocType','HomePage Settings')
	webnotes.model.delete_doc('DocType','Badge Settings')
	sql("update tabDocType set module='Home' where module in ('Event Updates', 'My Company')")
	sql("update tabPage set module='Home' where module in ('Event Updates', 'My Company')")
	sql("update `tabSearch Criteria` set module='Home' where module in ('Event Updates', 'My Company')")


	delete_pages = ('Chat User Gallery', 'Badge Info', 'Home', 'Website Setup', 'Test Page', 'Setup Masters', 'Service', 'Selling', 'Sales Reports', 'Organize','My Cart', 'My Activity', 'Manage Users', 'Maintenance', 'Getting Started', 'Gantt Test', 'Custom Reports - Stock', 'Custom Reports - Selling', 'Custom Reports - Production', 'Custom Reports - Payroll', 'Custom Reports - Maintenance', 'Custom Reports - Buying', 'Custom Reports - Accounts', 'CRM Setup', 'CRM Reports')
	for p in delete_pages:
	  webnotes.model.delete_doc('Page',p)
elif patch_no == 278:
	sql("update tabDocTrigger set method = 'home.update_feed' where method = 'event_updates.update_feed'")
elif patch_no == 279:
	dt = ['GL Entry', 'Stock Ledger Entry']
	for t in dt:
		rec = sql("select voucher_type, voucher_no, ifnull(is_cancelled, 'No') from `tab%s` where modified >= '2011-06-15 01:00:00' group by voucher_no" % t)
		for d in rec:
			sql("update `tab%s` set docstatus = %s where name = '%s'" % (d[0], d[2]=='No' and 1 or 2, d[1]))

	other_dt = ['Enquiry', 'Quotation', 'Sales Order', 'Indent', 'Purchase Order', 'Production Order', 'Customer Issue', 'Installation Note']
	for dt in other_dt:
		rec = sql("select name, status from `tab%s` where modified >= '2011-06-15 01:00:00'" % dt)
		for r in rec:
			sql("update `tab%s` set docstatus = %s where name = '%s'" % (dt, (r[1] in ['Submitted', 'Closed'] and 1 or r[1]=='Cancelled' and 2 or 0), r[0]))
elif patch_no == 280:
	reload_doc('accounts', 'doctype', 'form_16a')
elif patch_no == 281:
	dt_list = ['Delivery Note', 'Purchase Receipt']
	for dt in dt_list:
		sql("update `tab%s` set status = 'Submitted' where docstatus = 1 and modified >='2011-06-15 01:00:00'" % dt)
		sql("update `tab%s` set status = 'Cancelled' where docstatus = 2 and modified >='2011-06-15 01:00:00'" % dt)
elif patch_no == 282:
	dt_list = ['Enquiry', 'Quotation', 'Sales Order', 'Indent', 'Purchase Order', 'Production Order', 'Customer Issue', 'Installation Note', 'Receivable Voucher', 'Payable Voucher', 'Delivery Note', 'Purchase Receipt', 'Journal Voucher', 'Stock Entry']
	for d in dt_list:
		tbl = sql("select options from `tabDocField` where fieldtype = 'Table' and parent = '%s'" % d)
		for t in tbl:
			sql("update `tab%s` t1, `tab%s` t2 set t1.docstatus = t2.docstatus where t1.parent = t2.name" % (t[0], d))
elif patch_no == 283:
	rec = sql("select voucher_type, voucher_no, ifnull(is_cancelled, 'No') from `tabGL Entry` where modified >= '2011-06-15 01:00:00' order by name ASC")
	for d in rec:
		sql("update `tab%s` set docstatus = %s where name = '%s'" % (d[0], d[2]=='No' and 1 or 2, d[1]))
elif patch_no == 284:
	reload_doc('support', 'doctype', 'support_ticket')
	sql("update `tabDocField` set in_filter = 1 where fieldname in ('raised_by', 'subject') and parent = 'Support Ticket'")
elif patch_no == 286:
	reload_doc('accounts', 'search_criteria', 'itemwise_sales_register')
	reload_doc('accounts', 'search_criteria', 'itemwise_purchase_register')
elif patch_no == 287:
	sql("update `tabDocField` set no_copy = 1 where fieldname in ('per_received', 'per_billed', 'per_delivered') and parent in ('Purchase Order', 'Purchase Receipt', 'Sales Order', 'Delivery Note')")
elif patch_no == 288:
	reload_doc('accounts', 'doctype', 'payable_voucher')
elif patch_no == 289:
	sql("update `tabDocType` set subject = 'From %(supplier_name)s worth %(grand_total)s due on %(due_date)s | %(outstanding_amount)s outstanding' where name = 'Payable Voucher'")
	sql("update `tabDocType` set search_fields = 'status,transaction_date,customer,lead,order_type' where name = 'Quotation'")
elif patch_no == 290:
	count = sql("""SELECT * FROM  `tabModule Def`
		   WHERE `module_name` LIKE 'Home'""")
	if not count:
		md = Document('Module Def')
		md.module_name = 'Home'
		md.module_label = 'Home'
		md.save(1)
elif patch_no == 291:
	reload_doc('utilities','doctype','rename_tool')
elif patch_no == 292:
	reload_doc('accounts', 'search_criteria', 'trial_balance')
elif patch_no == 293:
	sql("delete from tabDocField where parent='Account' and fieldname='address'")
	reload_doc('accounts', 'doctype', 'account')
elif patch_no == 294:
	# new account profile fix
	ul = sql("select name from tabProfile where ifnull(name,'') not in ('Administrator', 'Guest', '')")
	# if one user and one user has no roles
	if len(ul)==1 and not sql("select parent from tabUserRole where role='System Manager' and parent=%s", ul[0][0]):
		get_obj('Setup Control').add_roles(Document('Profile', ul[0][0]))
elif patch_no == 295:
	sql("update `tabDocField` set options = 'Delivered\nNot Delivered\nPartly Delivered\nClosed\nNot Applicable' where parent = 'Sales Order' and fieldname = 'delivery_status'")
	sql("update `tabDocField` set options = 'Billed\nNot Billed\nPartly Billed\nClosed' where parent = 'Sales Order' and fieldname = 'billing_status'")
elif patch_no == 296:
	sql("delete from tabDocField where parent='Support Ticket' and fieldname='contact_no'")
	reload_doc('support', 'doctype', 'support_ticket')
elif patch_no == 297:
	reload_doc('hr', 'doctype', 'employee')
	reload_doc('hr', 'doctype', 'attendance')
	reload_doc('hr', 'doctype', 'expense_voucher')
	reload_doc('hr', 'doctype', 'appraisal')
	reload_doc('hr', 'doctype', 'salary_structure')
	reload_doc('hr', 'doctype', 'salary_slip')
elif patch_no == 298:
	sql("update `tabDocField` set options = 'link:Company' where parent = 'Attendance' and fieldname = 'company'")
	sql("update `tabDocField` set options = 'link:Company' where parent = 'Expense Voucher' and fieldname = 'company'")
	sql("update `tabDocField` set options = 'link:Company' where parent = 'Appraisal' and fieldname = 'company'")
elif patch_no == 299:
	sql("update `tabDocPerm` set `match` = NULL where parent = 'Employee' and role = 'Employee'")
elif patch_no == 300:
	sql("""DELETE FROM `tabSearch Criteria` WHERE name IN
		   ('sales_register1', 'sales_register2', 'purchase_register1')""")