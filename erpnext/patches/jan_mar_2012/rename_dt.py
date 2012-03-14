def execute():
	import webnotes
	from webnotes.model import rename, delete_doc
	from webnotes.model.code import get_obj
	from wnf import replace_code
	import os
	 

	# delete dt
	#-------------
	del_mapper = ['Production Forecast-Production Planning Tool', 'Production Forecast-Production Plan']
	for d in del_mapper:
		delete_doc('DocType Mapper', d)

	del_dt = ['Widget Control', 'Update Delivery Date Detail', 'Update Delivery Date', 'Tag Detail', 'Supplier rating', 'Stylesheet', 'Question Tag', 'PRO PP Detail', 'PRO Detail', 'PPW Detail', 'PF Detail', 'Personalize', 'Patch Util', 'Page Template', 'Module Def Role', 'Module Def Item', 'File Group', 'File Browser Control', 'File', 'Educational Qualifications', 'Earn Deduction Detail', 'DocType Property Setter', 'Contact Detail', 'BOM Report Detail', 'BOM Replace Utility Detail', 'BOM Replace Utility', 'Absent Days Detail', 'Activity Dashboard Control', 'Raw Materials Supplied', 'Setup Wizard Control', 'Company Group'] # docformat

	for d in del_dt:
		delete_doc('DocType', d)


	# Rename dt	
	#-------------
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
		'DocLayer'					:	'Customize Form View',
		'DocLayerField'				:	'CFV Field',
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

	for d in rendt:
		print d + ' --------> '+ rendt[d]

		#rename
		rename('DocType', d, rendt[d], 1)

		# update txt
		obj = get_obj('DocType', rendt[d])
		obj.doc.save()


		# RUN ONLY IN LOCAL
		######################


		# replace dt in js/py file
		for extn in ['js', 'py', 'txt']:
			replace_code('/var/www/erpnext/', d, rendt[d], extn)

		





	

#------TO-DO--------
# remove dir
# git remove
# dt mapper rename
# change in gl mapper
