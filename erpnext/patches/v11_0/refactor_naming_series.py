# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import print_function, unicode_literals

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

doctype_series_map = {
	'Additional Salary': 'HR-ADDSAL-.YYYY.-',
	'Appraisal': 'HR-APP-.YYYY.-',
	'Asset': 'AST-AST-.YYYY.-',
	'Asset Maintenance Log': 'AST-AML-.YYYY.-',
	'Asset Repair': 'AST-AREP-.YYYY.-',
	'Attendance': 'HR-ATT-.YYYY.-',
	'Auto Repeat': 'DESK-AREP-.YYYY.-',
	'Blanket Order': 'MAN-BOR-.YYYY.-',
	'C-Form': 'ACC-CF-.YYYY.-',
	'Campaign': 'SA-CAM-.YYYY.-',
	'Clinical Procedure': 'HEA-CPRO-.YYYY.-',
	'Course Schedule': 'EDU-CSCH-.YYYY.-',
	'Customer': 'SA-CUS-.YYYY.-',
	'Delivery Note': 'STO-DN-.YYYY.-',
	'Delivery Trip': 'STO-DT-.YYYY.-',
	'Driver': 'HR-DRI-.YYYY.-',
	'Employee': 'HR-EMP-.YYYY.-',
	'Employee Advance': 'HR-EADV-.YYYY.-',
	'Expense Claim': 'HR-EXP-.YYYY.-',
	'Fee Schedule': 'EDU-FSC-.YYYY.-',
	'Fee Structure': 'EDU-FST-.YYYY.-',
	'Fees': 'EDU-FEE-.YYYY.-',
	'Inpatient Record': 'HEA-IREC-.YYYY.-',
	'Installation Note': 'SA-ISN-.YYYY.-',
	'Instructor': 'EDU-INS-.YYYY.-',
	'Issue': 'SUP-ISS-.YYYY.-',
	'Journal Entry': 'ACC-JV-.YYYY.-',
	'Lab Test': 'HEA-LT-.YYYY.-',
	'Landed Cost Voucher': 'STO-LCV-.YYYY.-',
	'Lead': 'CRM-LEA-.YYYY.-',
	'Leave Allocation': 'HR-LAL-.YYYY.-',
	'Leave Application': 'HR-LAP-.YYYY.-',
	'Maintenance Schedule': 'MTN-MSCH-.YYYY.-',
	'Maintenance Visit': 'MTN-MV-.YYYY.-',
	'Material Request': 'STO-MREQ-.YYYY.-',
	'Member': 'NP-MEM-.YYYY.-',
	'Opportunity': 'CRM-OPP-.YYYY.-',
	'Packing Slip': 'STO-PS-.YYYY.-',
	'Patient': 'HEA-PAT-.YYYY.-',
	'Patient Encounter': 'HEA-PENC-.YYYY.-',
	'Patient Medical Record': 'HEA-PMR-.YYYY.-',
	'Payment Entry': 'ACC-PAYE-.YYYY.-',
	'Payment Request': 'ACC-PREQ-.YYYY.-',
	'Production Plan': 'MAN-PPLN-.YYYY.-',
	'Project Update': 'PRO-PRUP-.YYYY.-',
	'Purchase Invoice': 'PU-INV-.YYYY.-',
	'Purchase Order': 'PU-PO-.YYYY.-',
	'Purchase Receipt': 'STO-PREC-.YYYY.-',
	'Quality Inspection': 'STO-QINS-.YYYY.-',
	'Quotation': 'SAL-QTN-.YYYY.-',
	'Request for Quotation': 'PU-RFQ-.YYYY.-',
	'Sales Invoice': 'SA-INV-.YYYY.-',
	'Sales Order': 'SAL-SO-.YYYY.-',
	'Sample Collection': 'HEA-SC-.YYYY.-',
	'Shareholder': 'ACC-SH-.YYYY.-',
	'Stock Entry': 'STO-STE-.YYYY.-',
	'Stock Reconciliation': 'STO-SREC-.YYYY.-',
	'Student': 'EDU-STU-.YYYY.-',
	'Student Applicant': 'EDU-SAP-.YYYY.-',
	'Supplier': 'PU-SUP-.YYYY.-',
	'Supplier Quotation': 'PU-SUPQ-.YYYY.-',
	'Supplier Scorecard Period': 'PU-SSP-.YYYY.-',
	'Timesheet': 'PRO-TS-.YYYY.-',
	'Vehicle Log': 'HR-VLOG-.YYYY.-',
	'Warranty Claim': 'SUP-WCLA-.YYYY.-',
	'Work Order': 'MAN-WO-.YYYY.-'
}

def execute():
	series_to_set = get_series()
	for doctype, opts in series_to_set.items():
		set_series(doctype, opts["options"], opts["default"])

def set_series(doctype, options, default):
	make_property_setter(doctype, "naming_series", "options", options, "Text")
	make_property_setter(doctype, "naming_series", "default", default, "Text")

def get_series():
	series_to_set = {}

	for doctype, new_series in doctype_series_map.items():
		if not frappe.db.a_row_exists(doctype):
			continue

		series_to_preserve = get_series_to_preserve(doctype)
		default_series = get_default_series(doctype)
		if not default_series:
			continue
		if not series_to_preserve:
			continue
		existing_series = frappe.db.get_value('DocField', {'parent': doctype, 'fieldname': 'naming_series'}, 'options').split("\n")
		existing_series = filter(None, [d.strip() for d in existing_series])

		# set naming series property setter
		series_to_preserve = list(set(series_to_preserve + existing_series))
		if series_to_preserve:
			series_to_set[doctype] = {"options": "\n".join(series_to_preserve), "default": default_series}

	return series_to_set

def get_series_to_preserve(doctype):
	series_to_preserve = frappe.db.sql_list("""select distinct naming_series from `tab{doctype}`""".format(doctype=doctype))
	series_to_preserve.sort()
	return series_to_preserve

def get_default_series(doctype):
	default_series = frappe.db.sql("""select naming_series from `tab{doctype}`
		where creation=(select max(creation) from `tab{doctype}`) order by creation desc limit 1""".format(doctype=doctype))

	if not (default_series and default_series[0][0]):
		return
	return default_series[0][0]
