#Cleanup all unwanted documents and restructure of moduloes
#----------------------------------------------------------

import webnotes
from webnotes.model import delete_doc
from webnotes.modules.module_manager import reload_doc
from webnotes.modules.export_module import export_to_files
sql = webnotes.conn.sql


#----------------------------

def delete_unwanted_doctypes():
	"deletes doctypes which are not used anymore"
	
	try:
		sql("delete from `tabMenu Item`")
		sql("delete from tabDocField where fieldname = 'site_map_details' and parent ='Control Panel'")
	except:
		pass
		
	lst = ['Zone',  'WN Account Control', 'Wiki Page', 'Wiki History', 'Wiki Control', 'While You Were Out', 'Web Visitor', 'Tweet', 'Transfer Utility', 'Transfer Module', 'Transfer Control', 'Transfer Account', 'Tips Common', 'TestTabDT', 'TestDT', 'Test Type', 'Test Run', 'Test Record Detail', 'Test Record', 'Test Case', 'Supplier TDS Category Detail', 'Shopping Cart Control', 'Service Series', 'Series Detail', 'Rule Engine', 'RFQ', 'Report Filter Detail', 'Report Field Detail','Report Control', 'Rating Widget Record', 'Rating Widget Control', 'Rating Template Detail', 'Rating Template', 'PV Ded Tax Detail', 'PV Add Tax Detail', 'Product Variant', 'Product Variance', 'Product Group', 'Product Feature', 'Payroll Tips Common', 'Payroll Rule', 'Password Control', 'Page Visit', 'Patch', 'Multiple Transfer', 'Module Tip Control', 'Module Setter', 'Module Manager', 'Module Import', 'Module Detail', 'Message Control', 'Message', 'Mail Participant Details', 'Mail', 'Leave Type Detail', 'Leave Detail', 'Leave Applicable Detail', 'Lead Item Detail', 'Lead Attachment Detail', 'Item Attachments Detail', 'Instant Message', 'Impact Analysis', 'Forum Topic', 'Forum Control', 'Form Settings', 'Follower', 'ERP Setup', 'Enquiry Attachment Detail', 'Documentation', 'Condition Detail', 'Complaint Note', 'Code History', 'Code Editor', 'Code Backup Control', 'Code Backup', 'City', 'Change Log', 'Business Letter Type', 'Business Letter Template', 'Business Letter', 'Badge Settings Detail', 'Application Type', 'Application', 'Action Detail', 'Accounts Setup', 'Stock Common', 'Job Application', 'Service Schedule', 'Comment Control', 'Bank', 'Tag Widget Control', 'Feature Update', 'RFQ Detail', 'Supplier Quotation Detail', 'Supplier Quotation', 'Year Closing Voucher', 'Approval Structure', 'Site Map Detail', 'Menu Control', 'Menu Item', 'Menu Item Role'] # bank
	for d in lst:
		try:
			sql("delete from `tabProperty Setter` where select_doctype = '%s'" % d)
			sql("delete from `tabCustom Script` where dt = '%s'" % d)
			sql("delete from `tabCustom Field` where dt = '%s'" % d)
			delete_doc('DocType', d)
		except:
			pass
	
		
	sql("commit")	
	delete_tables(lst)
		
def delete_tables(lst):
	for d in lst:
		for t in ['tab', 'arc']:
			try:
				sql("drop table `%s%s`" % (t, d))
			except:
				continue
	
def delete_unwanted_pages():
	"deletes pages which are not used anymore"
	lst = ['Transaction Authorization', 'Prduct Display', 'Data Import', 'Partner Home', 'Product Display', 'Module Settings', 'About Us', 'Custom Reports', 'MIS', 'MIS - Comparison Report', 'Monthly MIS', 'MyReports', 'Navigation Page', 'Point Race', 'Tag Widget', 'Widget Test', 'Yearly MIS']
	for d in lst:
		try:
			delete_doc('Page', d)
		except:
			pass
			
			
def delete_unwanted_search_criteria():
	"deletes search criteria which are not used anymore"
	
	sql("update `tabSearch Criteria` set module = 'HR' where name = 'salary_structure_details'")
	
	lst = ['_SRCH00002', '_SRCH00001', 'warranty-amc_summary1', 'test_so4', 'test_so3', 'test_so2', 'test_so1', 'test_so', 'test5', 'target_variance_report1', 'STDSRCH/00006', 'STDSRCH/00005', 'STDSRCH/00004', 'STDSRCH/00003', 'STDSRCH/00002', 'STDSRCH/00001', 'so_pending_items_6', 'so_pending_items_5', 'so_pending_items_3', 'so_pending_items_34', 'scrap', 'sales_report_test', 'salary_structure_details1', 'salary_structure_details2', 'salary_structure_details3', 'salary_slips1', 'projectwise_pending_qty_and_costs2', 'projectwise_pending_qty_and_costs1', 'projectwise_delivered_qty_and_costs1', 'projectwise_delivered_qty_and_costs2', 'New Search Criteria 1', 'monthly_salary_register2', 'monthly_salary_register1', 'installed_items','follow_up_history', 'follow_up_report', 'employee_in_company_experience2', 'employee_in_company_experience1', 'employee_in_company_experience', 'employee_details', 'employee_details1', 'employee_details2', 'employees_birthday1', 'draft_so_pending_items', 'draft_sales_orders', 'delivery_notewise_pending_qty_to_install', 'datewise_leave_report2', 'datewise_leave_report1', 'datewise_leave_report', 'customer_issues1', 'cancelled_so_pending_items1', 'cancelled_so_pending_items', 'budget_variance_report3', 'budget_variance_report1', 'account_-_inputs_rg_23_a_-_part_ii_wrong_one', 'territory_item_group_wise_gp', 'sales_orderwise_pending_packing_item_summary', 'itemwise_trend', 'monthly_attendance_details_old', 'projectwise_contribution_report', 'projectwise_delivery_and_material_cost', 'projectwise_delivery_and_mat_cost_report', 'territorywise_trend', 'test_dn', 'rfq', 'rfq1']
	
	for d in lst:
		if sql("select name from `tabSearch Criteria` where ifnull(standard, 'Yes') = 'Yes' and name = '%s'" % d):
			try:
				delete_doc('Search Criteria', d)
			except:
				pass
		
	
def delete_unwanted_mappers():
	"deletes unwanted mappers"
	
	lst = ['Customer Issue-Maintenance Report', 'Enquiry-Service Quotation', 'Sales Order-Maintenance Report', 'Service Quotation-Service Order', 'Supplier Quotation-Purchase Order', 'Visit Schedule-Maintenance Report', 'RFQ-Supplier Quotation', 'Indent-RFQ']
	for d in lst:
		try:
			delete_doc('DocType Mapper', d)
		except:
			pass	
			
def delete_unwanted_modules():
	"deletes unwanted modules"
	lst = ['Development', 'Recycle Bin', 'Testing', 'Testing System', 'Test', 'Partner Updates', 'My Company', 'Event Updates', 'E-Commerce']
	for d in lst:
		try:
			delete_doc('Module Def', d)
		except:
			pass

#---------------------------------------------	

def rename_merge_modules():
	"Rename module as per users view and merge for removing confusion"
	
	rename_lst = [['CRM', 'Selling'], ['SRM','Buying'], ['Material Management', 'Stock'], ['Payroll','HR'], ['Maintenance', 'Support']]
	for d in rename_lst:
		# create new module manually and export to file???????
		reload_doc(d[1].lower(), 'Module Def', d[1])

	merge_lst = [['Tools', 'Utilities'], ['Application Internal', 'Utilities'], ['Settings', 'Setup']]
	# settings hardcoded in my_company
	# module hardcoded in home_control
	# material_management hardcoded in installation note
	# maintenance hardcoded in support_email_settings
	
	lst = rename_lst + merge_lst
	for d in lst:
		update_module(d[0], d[1])
		try:
			delete_doc('Module Def', d[0])
		except:
			pass
	reload_doc('Utilities', 'Module Def', 'Utilities')
	
def update_module(from_mod, to_mod):
	for t in ['DocType', 'Page', 'Search Criteria', 'DocType Mapper', 'Print Format', 'Role']:
		sql("update `tab%s` set module='%s' where module = '%s'"% (t, to_mod, from_mod))
		
#------------------------------------ 
def sync_roles():
	"Put Roles into corresponding module and delete Roles module"
	
	# roles
	roles = {
		'Accounts'	:		"'Accounts Manager', 'Accounts User', 'Auditor'", 
		'Selling'	: 		"'Customer', 'Sales User', 'Sales Manager', 'Sales Master Manager', 'Partner'", 
		'Buying'	:		"'Supplier', 'Purchase User', 'Purchase Manager', 'Purchase Master Manager'", 
		'Stock'		:		"'Material User', 'Material Master Manager', 'Material Manager', 'Quality Manager'", 
		'Support'	:		"'Support Team', 'Support Manager', 'Maintenance User', 'Maintenance Manager'", 
		'Production':		"'Production User', 'Production Manager', 'Production Master Manager'", 
		'Setup'		:		"'System Manager'", 
		'Projects'	:		"'Projects User'", 
		'HR'		:		"'HR User', 'HR Manager', 'Employee'",
		'Core'		:		"'Administrator', 'All', 'Guest'"
	}
	for mod in roles.keys():
		sql("update `tabRole` set module = '%s' where name in (%s)" % (mod, roles[mod]))
		
	sql("update `tabDocType` set module = 'Setup' where name = 'Role'")
	try:
	
		delete_doc('Module Def', 'Roles')
	except:
		pass
#------------------------------------ 
def sync_mapper():
	"Put mappers into corresponding module"
		
	mappers = {
		'Accounts':		('Delivery Note-Receivable Voucher', 'Project-Receivable Voucher', 'Purchase Order-Payable Voucher', 'Purchase Receipt-Payable Voucher', 'Sales Order-Receivable Voucher'), 
		'Selling': 		('Delivery Note-Installation Note', 'Enquiry-Quotation', 'Lead-Enquiry', 'Lead-Customer', 'Project-Sales Order', 'Quotation-Sales Order', ), 
		'Buying':		('Indent-Purchase Order', 'Sales Order-Indent'), 
		'Stock':		('Purchase Order-Purchase Receipt', 'Project-Delivery Note', 'Receivable Voucher-Delivery Note', 'Sales Order-Delivery Note'), 
		'Support':		('Customer Issue-Maintenance Visit', 'Sales Order-Maintenance Schedule', 'Sales Order-Maintenance Visit'), 
		'Production':	('Production Forecast-Production Plan', 'Production Forecast-Production Planning Tool', 'Sales Order-Production Plan'), 
		'HR':			('KRA Template-Appraisal', 'Salary Structure-Salary Slip')
	}
	
	for mod in mappers.keys():
		sql("update `tabDocType Mapper` set module = '%s' where name in %s" % (mod, mappers[mod]))
	try:
		delete_doc('Module Def', 'Mapper')
	except:
		pass
# --------------------------------------
# function below will be run only in localhost
'''def export_docs():
	"""
		Export all documents where module has been changed
	"""
	for dtype in ['DocType', 'Page', 'Search Criteria', 'DocType Mapper', 'Print Format', 'Role']:
		lst = sql("select name, module from `tab%s`" % dtype)
		for rec in lst:
			webnotes.msgprint(rec)
			if rec and rec[0] and rec[1]:
				export_to_files(record_list = [[dtype, rec[0]]], record_module = rec[1])

	#grep test company
'''

#---------------------------------------
def run_patches():
	# update module
	dt_module = {'LC PR Detail':'Stock', 'Landed Cost Detail':'Stock', 'Comment Widget Record': 'Core', 'Tag':'Core', 'Tag Detail': 'Core', 'POS Settings': 'Accounts', 'Menu Item': 'Setup', 'Menu Item Role': 'Setup'}
	for d in dt_module.keys():
		sql("update `tabDocType` set module = '%s' where name = '%s'" % (dt_module[d], d))
	delete_unwanted_mappers()
	delete_unwanted_doctypes()
	sql("start transaction")
	delete_unwanted_pages()

	delete_unwanted_search_criteria()

	
	rename_merge_modules()
	sync_roles()
	sync_mapper()
	delete_unwanted_modules()
	# landed cost wizard link in stock
	reload_doc('stock', 'Module Def', 'Stock')
	
	sql("commit")
