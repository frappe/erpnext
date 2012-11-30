from __future__ import unicode_literals
import webnotes
import conf
import webnotes.model
from wnf import replace_code
from termcolor import colored
from webnotes.modules import reload_doc
from webnotes.utils import make_esc
import os

def execute1():
	#rendt = get_dt_to_be_renamed()
	#rename_dt_files(rendt)
	#update_local_file_system()
	replace_labels_with_fieldnames()

def execute():

	#---------------------------------------------------
	# doctype renaming
	rendt = get_dt_to_be_renamed()
	# Rename dt	in db
	rename_in_db(rendt, 'DocType', 1)
	# Upadte dt in records
	update_dt_in_records(rendt)

	#---------------------------------------------------
	# Dt Mapper renaming
	ren_mapper = get_mapper_to_be_renamed()
	# Rename mapper in db
	rename_in_db(ren_mapper, 'DocType Mapper', 0)

	#---------------------------------------------------
	# GL Mapper renaming
	gl_mapper = {'Receivable Voucher': 'Sales Invoice', 'Payable Voucher': 'Purchase Invoice'}
	rename_in_db(gl_mapper, 'GL Mapper', 0)


	#---------------------------------------------------
	# remove dt label
	webnotes.conn.sql("""delete from `tabDocType Label` where name in ('Ticket', 'Receivable Voucher', 
		'QA Inspection Report', 'Payable Voucher', 'Manage Account', 'Indent', 'DocLayer')""")

	#---------------------------------------------------
	# Reload mapper from file
	for d in ren_mapper:
		mod = '_'.join(webnotes.conn.sql("select module from `tabDocType Mapper` where name = %s", 
			ren_mapper[d])[0][0].lower().split())
		reload_doc(mod, 'DocType Mapper', ren_mapper[d])

	delete_search_criteria()
	change_report_module()

	# reload custom search criteria
	#for d in  webnotes.conn.sql("""select name, module from
	#		`tabSearch Criteria` where ifnull(standard, 'No') = 'Yes' and ifnull(disabled, 0) = 0"""):
	#
	for path, folders, files in os.walk(conf.modules_path):
		if not path.endswith('search_criteria'): continue
		module = path.split(os.sep)[-2]
		for sc in folders:
			try:
				reload_doc(module, 'search_criteria', sc)
				print module, sc
			except Exception, e:
				print "did not reload: " + str(d)
	
	webnotes.conn.sql("""DELETE FROM `tabPrint Format`
			WHERE name IN ('Delivery Note Format', 'Purchase Order Format',
			'Quotation Format', 'Receivable Voucher Format', 'Sales Order',
			'SalesInvoiceModern_test', 'SalesInvoiceStdNew',
			'Service Order Format', 'Service Quotation Format')""")

	# reload custom print format
	for d in webnotes.conn.sql("""select name, module from `tabPrint Format`
			where ifnull(standard, 'No') = 'Yes'"""):
		try:
			reload_doc(d[1], 'Print Format', d[0])
		except Exception, e:
			print "did not reload: " + str(d)

	#  Reload GL Mapper
	for d in webnotes.conn.sql("select name from `tabGL Mapper`"):
		reload_doc('accounts', 'GL Mapper', d[0])
	reload_doc('accounts', 'GL Mapper', 'Purchase Invoice with write off')

	webnotes.conn.sql("update `tabDocType` set module = 'Utilities' where module = 'Knowledge Base'")
	webnotes.conn.sql("update `tabPage` set module = 'Utilities' where module = 'Knowledge Base'")

		

def delete_search_criteria():
	webnotes.conn.sql("""DELETE FROM `tabSearch Criteria`
			WHERE name IN ('', 'bills-to_be_paid',
			'bills-to_be_submitted', 'cenvat_credit_-_input_or_capital_goods',
			'appraisal_custom', 'custom_test', 'custom_test1', 'delivery_note-to_be_billed',
			'delivery_note-to_be_submitted', 'delivery_notes',
			'employee_leave_balance_report', 'flat_bom_report',
			'general_ledger1', 'lead_interested',
			'payables_-_as_on_outstanding', 'periodical_budget_report',
			'projectwise_delivered_qty_and_costs_as_per_purchase_cost',
			'projectwise_pending_qty_and_costs_as_per_purchase_cost', 'sales',
			'sales_order1', 'sales_order_pending_items',
			'territory_wise_sales_-_target_vs_actual_', 'test_report',
			'lease_agreement_list', 'lease_monthly_future_installment_inflows',
			'lease_over_due_list', 'lease_overdue_age_wise',
			'lease_receipt_summary_month_wise', 'lease_receipts_client_wise',
			'lease_yearly_future_installment_inflows',
			'monthly_ledger_summary_report', 'payables_-_as_on_outstanding',
			'payment_report', 'progressive_total_excise_duty',
			'service_tax_credit_account_-_inputs',
			'total_amout_collection_for_a_period_-_customerwise',
			'invoices-to_be_submitted', 'invoices-to_receive_payment',
			'opportunity-quotations_to_be_sent', 'purchase_order-to_be_billed',
			'purchase_order-to_be_submitted',
			'purchase_order-to_receive_items',
			'purchase_request-purchase_order_to_be_made',
			'purchase_request-to_be_submitted',
			'sales-order_to_be_submitted', 'sales_order-overdue',
			'sales_order-to_be_billed', 'sales_order-to_be_delivered',
			'sales_order-to_be_submitted', 'task-open', 'appraisal_custom',
			'employee_details', 'employee_in_company_experience',
			'employee_leave_balance_report', 'employeewise_leave_transaction_details',
			'pending_appraisals', 'pending_expense_claims', 'delivery_plan', 'flat_bom_report',
			'dispatch_report', 'projectwise_delivered_qty_and_costs_as_per_purchase_cost', 
			'projectwise_pending_qty_and_costs_as_per_purchase_cost', 'custom_test', 'custom_test1',
			'delivery_notes', 'delivery_note_disabled', 'lead', 'lead_interested', 'lead_report',
			'periodic_sales_summary', 'monthly_despatched_trend', 'sales', 'sales_order',
			'sales_order1', 'sales_agentwise_commission', 'test_report', 
			'territory_wise_sales_-_target_vs_actual_', 
			'pending_po_items_to_bill1', 'pending_po_items_to_receive1', 
			'expense_vouchers', 'pending_expense_vouchers', 'shortage_to_indent')""")

	webnotes.conn.sql("""
		DELETE FROM `tabSearch Criteria`
		WHERE name IN ('monthly_transaction_summary', 'trend_analyzer',
		'yearly_transaction_summary', 'invoices-overdue', 'lead-to_follow_up',
		'opportunity-to_follow_up', 'serial_no-amc_expiring_this_month',
		'serial_no-warranty_expiring_this_month')
		AND IFNULL(standard, 'No') = 'Yes'
		""")

def change_report_module():
	reports = {'itemwise_receipt_details': 'Stock'}
	for k in reports:
		webnotes.conn.sql("update `tabSearch Criteria` set module = %s where name = %s", (reports[k], k))

def rename_in_db(ren_data, data_type, is_doctype):
	for d in ren_data:
		print colored('Renaming... ' + d + ' --> '+ ren_data[d], 'yellow')
		#rename
		try:
			webnotes.model.rename(data_type, d, ren_data[d], is_doctype)
		except Exception, e:
			if e.args[0]!=1050:
				raise e
			else:
				print e
				pass


def update_dt_in_records(rendt):
	for d in rendt:
		# Feed, property setter, search criteria, gl mapper, form 16A, naming series options, doclayer - dodtype is not mentioed in options
		dt_list = webnotes.conn.sql("""select t1.parent, t1.fieldname from
			tabDocField t1, tabDocType t2 where t1.parent = t2.name and
			t1.fieldname in ('dt', 'doctype', 'doc_type', 'dt_type') and
			ifnull(t1.options, '') = '' and ifnull(t2.issingle, 0) = 0 and
			t1.parent in ('Custom Field', 'Custom Script', 'Property Setter')""")
		for dt in dt_list:
			webnotes.conn.sql("update `tab%s` set %s = replace(%s, '%s', '%s') where %s = '%s'" % (dt[0], dt[1], dt[1], d, rendt[d], dt[1], d))

		# gl mapper, gl entry
		webnotes.conn.sql("update `tabGL Mapper Detail` set against_voucher_type = replace(against_voucher_type, '%s', '%s') where against_voucher_type like '%%%s%%'" % (d, rendt[d], d))
		webnotes.conn.sql("update `tabGL Entry` set against_voucher_type = replace(against_voucher_type, '%s', '%s') where against_voucher_type = '%s'" % (d, rendt[d], d))
		webnotes.conn.sql("update `tabGL Entry` set voucher_type = replace(voucher_type, '%s', '%s') where voucher_type = '%s'" % (d, rendt[d], d))

		# Stock ledger entry
		webnotes.conn.sql("update `tabStock Ledger Entry` set voucher_type = replace(voucher_type, '%s', '%s') where voucher_type = '%s'" % (d, rendt[d], d))

		# Custom fld: options
		webnotes.conn.sql("update `tabCustom Field` set options = replace(options, %s, %s) where fieldtype in ('Link', 'Select', 'Table')", (d, rendt[d]))
		
		#Property Setter: value (if property=options)
		webnotes.conn.sql("update `tabProperty Setter` set value = replace(value, %s, %s) where property = 'Options'", (d, rendt[d]))

		# custom script: script
		webnotes.conn.sql("update `tabCustom Script` set script = replace(script, %s, %s)", (d, rendt[d]))

		# print format: html
		webnotes.conn.sql("update `tabPrint Format` set html = replace(html, %s, %s) where ifnull(standard, 'Yes') = 'No'", (d, rendt[d]))

		# custom report: doc_type, filters, columns, parent_doc_type, add_cond, add_col, add_tab,
		#					dis_filters, group_by, sort_by, report_script, server_script, custom_query
		webnotes.conn.sql("""
			update
				`tabSearch Criteria` 
			set 
				doc_type		= replace(doc_type, %s, %s), 
				filters			= replace(filters, %s, %s), 
				columns			= replace(columns, %s, %s), 
				parent_doc_type = replace(parent_doc_type, %s, %s), 
				add_cond		= replace(add_cond, %s, %s), 
				add_col			= replace(add_col, %s, %s), 
				add_tab			= replace(add_tab, %s, %s), 
				dis_filters		= replace(dis_filters, %s, %s), 
				group_by		= replace(group_by, %s, %s), 
				sort_by			= replace(sort_by, %s, %s), 
				report_script	= replace(report_script, %s, %s), 
				server_script	= replace(server_script, %s, %s), 
				custom_query	= replace(custom_query, %s, %s)
			where 
				ifnull(standard, 'Yes') = 'No'
		""", (d, rendt[d], d, rendt[d], d, rendt[d], d, rendt[d], d, rendt[d], d, rendt[d], d, rendt[d], 
				d, rendt[d], d, rendt[d], d, rendt[d], d, rendt[d], d, rendt[d], d, rendt[d], ))




def get_dt_to_be_renamed():
	rendt = {
		'Receivable Voucher'		:	'Sales Invoice',
		'RV Detail'					:	'Sales Invoice Item',
		'RV Tax Detail'				:	'Sales Taxes and Charges',
		'Payable Voucher'			:	'Purchase Invoice',
		'PV Detail'					:	'Purchase Invoice Item',
		'Purchase Tax Detail'		:	'Purchase Taxes and Charges',
		'Indent'					:	'Purchase Request',
		'Indent Detail'				:	'Purchase Request Item',
		'QA Inspection Report'		:	'Quality Inspection',
		'Ticket'					:	'Task',
		'Manage Account'			:	'Global Defaults',
		'ToDo Item'					:	'ToDo',
		'Term'						:	'Terms and Conditions',
		'Static Parameter Detail'	:	'SMS Parameter',
		'SS Earning Detail'			:	'Salary Slip Earning',
		'SS Deduction Detail'		:	'Salary Slip Deduction',
		'Sales Order Detail'		:	'Sales Order Item',
		'Sales BOM Detail'			:	'Sales BOM Item',
		'Return Detail'				:	'Sales and Purchase Return Item',
		'Ref Rate Detail'			:	'Item Price',
		'Receiver Detail'			:	'SMS Receiver',
		'Quotation Detail'			:	'Quotation Item',
		'QA Specification Detail'	:	'Quality Inspection Reading',
		'Purchase Receipt Detail'	:	'Purchase Receipt Item',
		'Purchase Other Charges'	:	'Purchase Taxes and Charges Master',
		'PR Raw Material Detail'	:	'Purchase Receipt Item Supplied',
		'PP SO Detail'				:	'Production Plan Sales Order',
		'PP Detail'					:	'Production Plan Item',
		'PO Raw Material Detail'	:	'Purchase Order Item Supplied',
		'PO Detail'					:	'Purchase Order Item', 
		'Packing Slip Detail'		:	'Packing Slip Item',
		'Other Charges'				:	'Sales Taxes and Charges Master',
		'Order Lost Reason'			:	'Quotation Lost Reason',
		'Manage Account'			:	'Global Defaults',
		'Maintenance Visit Detail'	:	'Maintenance Visit Purpose',
		'Ledger Balance Export'		:	'Multi Ledger Report',
		'LC PR Detail'				:	'Landed Cost Purchase Receipt',
		'Landed Cost Detail'		:	'Landed Cost Item',
		'KRA Template'				:	'Appraisal Template',
		'KRA Sheet'					:	'Appraisal Template Goal',
		'Item Specification Detail' :	'Item Quality Inspection Parameter',
		'Item Maintenance Detail'	:	'Maintenance Schedule Item',
		'IR Payment Detail'			:	'Payment to Invoice Matching Tool Detail',
		'Internal Reconciliation'	:	'Payment to Invoice Matching Tool',
		'Installed Item Details'	:	'Installation Note Item',
		'Holiday List Detail'		:	'Holiday',
		'Follow up'					:	'Communication Log',
		'Flat BOM Detail'			:	'BOM Explosion Item',
		'Expense Voucher Detail'	:	'Expense Claim Detail',
		'Expense Voucher'			:	'Expense Claim',
		'Expense Type'				:	'Expense Claim Type',
		'Enquiry Detail'			:	'Opportunity Item',
		'Enquiry'					:	'Opportunity',
		'Earning Detail'			:	'Salary Structure Earning',
		'DocLayerField'				:	'Customize Form Field',
		'DocLayer'					:	'Customize Form',
		'Delivery Note Detail'		:	'Delivery Note Item',
		'Deduction Detail'			:	'Salary Structure Deduction',
		'Comment Widget Record'		:	'Comment',
		'BOM Material'				:	'BOM Item',
		'Bill Of Materials'			:	'BOM',
		'Appraisal Detail'			:	'Appraisal Goal',
		'Advance Allocation Detail' :	'Purchase Invoice Advance',
		'Advance Adjustment Detail' :	'Sales Invoice Advance',
		'Ledger Detail'				:	'Multi Ledger Report Detail',
		'TA Control'				:	'Trend Analyzer Control',
		'Sales and Purchase Return Wizard'	: 'Sales and Purchase Return Tool',
		'Educational Qualifications Detail' : 'Employee Education',
		'Delivery Note Packing Detail'		: 'Delivery Note Packing Item',
		'Experience In Company Detail'		: 'Employee Internal Work History',
		'Professional Training Details'		: 'Employee Training',
		'Previous Experience Detail'		: 'Employee External Work History',
	}
	return rendt


def get_mapper_to_be_renamed():
	ren_map = {
		'Sales Order-Receivable Voucher'	:	'Sales Order-Sales Invoice',
		'Sales Order-Indent'				: 	'Sales Order-Purchase Request',
		'Receivable Voucher-Delivery Note' 	: 	'Sales Invoice-Delivery Note',
		'Purchase Receipt-Payable Voucher'	: 	'Purchase Receipt-Purchase Invoice',
		'Purchase Order-Payable Voucher'	: 	'Purchase Order-Purchase Invoice',
		'Project-Receivable Voucher' 		: 	'Project-Sales Invoice',
		'Lead-Enquiry'						: 	'Lead-Opportunity',
		'KRA Template-Appraisal'			: 	'Appraisal Template-Appraisal',
		'Indent-Purchase Order'				: 	'Purchase Request-Purchase Order',
		'Enquiry-Quotation'					: 	'Opportunity-Quotation',
		'Delivery Note-Receivable Voucher'	: 	'Delivery Note-Sales Invoice'
	}
	return ren_map




#--------------------------------------------------------------------------------------------------------


def update_local_file_system():
	""" RUN ONLY IN LOCAL"""
	
	# doctype renaming
	rendt = get_dt_to_be_renamed()

	# replace dt in js/py file
	update_file_content(rendt)
	# git mv
	rename_dt_files(rendt)


	# Mapper renaming
	ren_mapper = get_mapper_to_be_renamed()

	rename_mapper_files(ren_mapper)

	os.system('git mv erpnext/accounts/GL\ Mapper/Payable\ Voucher erpnext/accounts/GL\ Mapper/Purchase\ Invoice')
	os.system('git mv erpnext/accounts/GL\ Mapper/Purchase\ Invoice/Payable\ Voucher.txt erpnext/accounts/GL\ Mapper/Purchase\ Invoice/Purchase\ Invoice.txt')
	os.system('git mv erpnext/accounts/GL\ Mapper/Receivable\ Voucher erpnext/accounts/GL\ Mapper/Sales\ Invoice')
	os.system('git mv erpnext/accounts/GL\ Mapper/Sales\ Invoice/Receivable\ Voucher.txt erpnext/accounts/GL\ Mapper/Sales\ Invoice/Sales\ Invoice.txt')
	
	# git rm production dt mapper
	os.system('git rm -r erpnext/production/DocType\ Mapper/')



def update_file_content(rendt):
	for d in rendt:
		print colored('Renaming... ' + d + ' --> '+ rendt[d], 'yellow')
		for extn in ['js', 'py', 'txt', 'html']:
			res = replace_code('/var/www/erpnext/', d, rendt[d], extn)
			if res == 'skip':
				break
		
		
def rename_dt_files(rendt):
	for d in rendt:
		mod = webnotes.conn.sql("select module from tabDocType where name = %s", rendt[d])[0][0]
		if mod == 'Core':
			os.chdir('/var/www/erpnext/lib/')
			path = 'py/core/doctype/'
		else:
			os.chdir('/var/www/erpnext/')
			path = 'erpnext/' + '_'.join(mod.lower().split()) + '/doctype/'
		old = '_'.join(d.lower().split())
		new = '_'.join(rendt[d].lower().split())

		print 'git mv ' + path + old + ' ' + path + new
		# rename old dir
		os.system('git mv ' + path + old + ' ' + path + new)

		# rename all files in that dir
		for extn in ['js', 'py', 'txt', 'html']:
			if os.path.exists(path + new + '/'+ old + '.' +extn):
				os.system('git mv ' + path + new + '/'+ old + '.' +extn + ' ' + path + new + '/' + new + '.' +extn)
				print 'git mv ' + path + new + '/'+ old + '.' +extn + ' ' + path + new + '/' + new + '.' +extn


def rename_mapper_files(ren_mapper):
	for d in ren_mapper:
		# module
		mod = '_'.join(webnotes.conn.sql("select module from `tabDocType Mapper` where name = %s", ren_mapper[d])[0][0].lower().split())
		path = 'erpnext/' + mod + '/DocType Mapper/'

		# rename old dir
		esc = make_esc('$ ')
		os.system('git mv ' + esc(path + d) + ' ' + esc(path + ren_mapper[d]))
		print 'git mv ' + esc(path + d) + ' ' + esc(path + ren_mapper[d])
		os.system('git mv ' + esc(path + ren_mapper[d] + '/'+ d + '.txt')
				+ ' ' + esc(path + ren_mapper[d] + '/' + ren_mapper[d] + '.txt'))
		print 'git mv ' + esc(path + ren_mapper[d] + '/'+ d + '.txt') + ' ' + esc(path + ren_mapper[d] + '/' + ren_mapper[d] + '.txt')
		

def replace_labels_with_fieldnames():
	"""
		This is used for replacing instances like cur_frm.cscript['LABEL'] with
		cur_frm.cscript.FIELDNAME in js files
	"""
	doctype = {}
	doctype.update(prepare_dict_of_label_fieldname('/var/www/erpnext/erpnext/'))
	doctype.update(prepare_dict_of_label_fieldname('/var/www/erpnext/lib/py'))
	#print doctype
	
	for doc in doctype:
		label_fieldname = doctype[doc]
		for d in label_fieldname:
			#label = "cur_frm.cscript['%s']" % d
			#fieldname = "cur_frm.cscript.%s" % label_fieldname[d]
			label = d
			fieldname = label_fieldname[d]
			print colored('Changing... ' + doc + ': ' + label + ' --> '+ fieldname, 'yellow')
			#res = replace_code('/var/www/erpnext/', label, fieldname, 'js')
			res = replace_code('/var/www/erpnext/', label, fieldname, 'js',
					'hide_field\(.*%s' % label)
			if res == 'skip':
				break

def prepare_dict_of_label_fieldname(module_path):
	from webnotes.model.utils import peval_doclist
	from webnotes.model.sync import get_file_path
	doctype = {}
	for path, folders, files in os.walk(module_path):
		if path == module_path:
			modules_list = folders
		for f in files:
			if f.endswith(".txt"):
				rel_path = os.path.relpath(path, conf.modules_path)
				path_tuple = rel_path.split(os.sep)
				if (len(path_tuple)==3 and path_tuple[0] in modules_list and
						path_tuple[1] == 'doctype'):
					file_name = f[:-4]
					with open(get_file_path(path_tuple[0], file_name), 'r') as fn:
						doclist = peval_doclist(fn.read())
						doctype[file_name] = dict(([d.get('label'),d.get('fieldname')] \
								for d in doclist if d.get('doctype')=='DocField'))
	return doctype
