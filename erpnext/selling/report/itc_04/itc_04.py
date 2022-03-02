# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import json
import math
from datetime import date

from frappe.utils import flt, formatdate, getdate
from six import iteritems

def execute(filters=None):
	columns = get_columns(filters)
	conditions = get_con(filters)
	data = get_data(filters, conditions)

	validate_filters(filters)

	return columns, data

def validate_filters(filters):
	if filters.report == "ITC-05 B" or filters.report == "ITC-05 C":
		frappe.throw(" This report is under Development. Please contact your Administrator ")

def get_columns(filters):
	if filters.report == "ITC-04":
		columns = [
			{
				"label": _("GSTIN of Job Worker(JW)"),
				"fieldtype": "Data",
				"fieldname": "gstin_of_job_worker",
				"width": 140
			},
			{
				"label": _("State"),
				"fieldtype": "Data",
				"fieldname": "state",
				"width": 140
			},
			{
				"label": _("Job Workers Type"),
				"fieldtype": "Data",
				"fieldname": "job_workers_type",
				"width": 140
			},
			{
				"label": _("Challan Number"),
				"fieldtype": "Link",
				"options": "Stock Entry",
				"fieldname": "challan_number",
				"width": 140
			},
			{
				"label": _("Challan Date"),
				"fieldtype": "Date",
				"fieldname": "challan_date",
				"width": 140
			},
			{
				"label": _("Types Of Goods"),
				"fieldtype": "Data",
				"fieldname": "types_of_goods",
				"default":"Inputs",
				"width": 140
			},
			{
				"label": _("Description Of Goods"),
				"fieldtype": "Data",
				"fieldname": "description_of_goods",
				"width": 140
			},
			{
				"label": _("Unique Quantity Code"),
				"fieldtype": "Data",
				"fieldname": "unique_quantity_code",
				"width": 140
			},
			{
				"label": _("Quantity"),
				"fieldtype": "Float",
				"fieldname": "quantity",
				"width": 140
			},
			{
				"label": _("Taxable Value"),
				"fieldtype": "Float",
				"fieldname": "taxable_value",
				"width": 100
			},
			{
				"label": _("Integrated Tax Rate In(%)"),
				"fieldtype": "Percent",
				"fieldname": "integrated_tax_rate",
				"width": 100
			},
			{
				"label": _("Central Tax Rate In (%)"),
				"fieldtype": "Percent",
				"fieldname": "central_tax_rate",
				"width": 100
			},
			{
				"label": _("State/Ut Tax Rate In (%)"),
				"fieldtype": "Percent",
				"fieldname": "state_ut_tax_rate",
				"width": 100
			},
			{
				"label": _("Cess Rate In (%)"),
				"fieldtype": "Percent",
				"fieldname": "cess",
				"width": 100
			},
		]
		return columns
	elif filters.report == "ITC-05 A":
		columns = [
			{
				"label": _("GSTIN of Job Worker(JW)"),
				"fieldtype": "Data",
				"fieldname": "gstin_of_job_worker",
				"width": 140
			},
			{
				"label": _("State"),
				"fieldtype": "Data",
				"fieldname": "state",
				"width": 140
			},
			{
				"label": _("Original Challan Number Issued by Principal"),
				"fieldtype": "Link",
				"fieldname": "original_challan_number_issued_by_principal",
				"width": 140,
				"options" : "Stock Entry"
			},
			{
				"label": _("Original Challan Date Issued by Principal"),
				"fieldtype": "Date",
				"fieldname": "original_challan_date_issued_by_principal",
				"width": 140
			},
			{
				"label": _("Challan Number Issued by Job Worker"),
				"fieldtype": "Data",
				"fieldname": "challan_number_issued_by_job_worker",
				"default": "Inputs",
				"width": 140
			},
			{
				"label": _("Challan Date Issued by Job Worker"),
				"fieldtype": "Date",
				"fieldname": "challan_date_issued_by_job_worker",
				"width": 140
			},
			{
				"label": _("Nature of Job Work Done"),
				"fieldtype": "Data",
				"fieldname": "nature_of_job_work_done",
				"width": 140
			},
			{
				"label": _("Description Of Goods"),
				"fieldtype": "Data",
				"fieldname": "description_of_goods",
				"width": 140
			},
			{
				"label": _("Unique Quantity Code (UQC)"),
				"fieldtype": "Data",
				"fieldname": "unique_quantity_code",
				"width": 140
			},
			{
				"label": _("Quantity"),
				"fieldtype": "Float",
				"fieldname": "quantity",
				"width": 140
			},
			{
				"label": _("Losses Unique Quantity Code (UQC)"),
				"fieldtype": "Data",
				"fieldname": "losses_uqc",
				"width": 190
			},
			{
				"label": _("Losses Quantity"),
				"fieldtype": "Float",
				"fieldname": "losses_quantity",
				"width": 140
			},
			{
				"label": _("To Be Named"),
				"fieldtype": "Float",
				"fieldname": "no_name",
				"width": 140
			},
			# {
			# 	"label": _("Central Tax Rate In (%)"),
			# 	"fieldtype": "Data",
			# 	"fieldname": "central_tax_rate",
			# 	"width": 100
			# },
			# {
			# 	"label": _("State/Ut Tax Rate In (%)"),
			# 	"fieldtype": "Data",
			# 	"fieldname": "state_ut_tax_rate",
			# 	"width": 100
			# },
			# {
			# 	"label": _("Cess"),
			# 	"fieldtype": "Data",
			# 	"fieldname": "cess",
			# 	"width": 100
			# },
		]
		return columns
	elif filters.report == "ITC-05 B" or filters.report == "ITC-05 C":	
		pass

def get_con(filters):
	date_dict = {}
	if filters.get('q_return'):
		fiscal_yr = str(filters.fiscal_year).split("-")
		start_date, end_date = None, None
		if filters.get('q_return') == "Apr-Jun":
			start_date = fiscal_yr[0]+'-04-01'
			end_date = fiscal_yr[0]+'-06-30'
		elif filters.get('q_return') == "July-Sept":
			start_date = fiscal_yr[0]+'-07-01'
			end_date = fiscal_yr[0]+'-09-30'
		elif filters.get('q_return') == "Oct-Dec":
			start_date = fiscal_yr[0]+'-10-01'
			end_date = fiscal_yr[0]+'-12-31'
		elif filters.get('q_return') == "Jan-March":
			start_date = fiscal_yr[1]+'-01-01'
			end_date = fiscal_yr[1]+'-03-31'
		elif filters.get('q_return') == "Apr-Sept":
			start_date = fiscal_yr[0]+'-04-01'
			end_date = fiscal_yr[0]+'-09-30'
		elif filters.get('q_return') == "Oct-March":
			start_date = fiscal_yr[0]+'-10-01'
			end_date = fiscal_yr[1]+'-03-31'	
		date_dict['start_date'] = start_date
		date_dict['end_date'] = end_date

	if filters.get('address'):
		date_dict['address'] = filters.get('address')
	return date_dict


def get_data(filters,conditions):
	if filters.report == "ITC-04":
		data = []
		s_d = "'"+conditions['start_date']+"'"
		m_d = "'"+conditions['end_date']+"'"
		query = """ select se.name as name from `tabStock Entry` se, `tabPurchase Order` po
		 						where se.purchase_order = po.name and se.docstatus = 1 and
		 						se.stock_entry_type = "Send to Subcontractor" and
		 						se.posting_date between {0} and {1}
		 						and se.company = '{2}' """.format(s_d,m_d,filters.get('company'))

		if filters.get('company_address'):
			query+= """ and po.billing_address = '{0}' """.format(filters.get('company_address'))

		se = frappe.db.sql(query,as_dict=1)

		for name in se:
			se_doc = frappe.get_doc("Stock Entry",name.name)
			po_doc = frappe.get_doc("Purchase Order",se_doc.purchase_order)
			tax_cat = po_doc.tax_category

			for row in se_doc.items:
				itm_obj = frappe.get_doc("Item",row.item_code)
				sgst, cgst, igst,cess = None, None, None, None
				for c_row in itm_obj.taxes:
					if c_row.tax_category == tax_cat:
						tax_temp_obj = frappe.get_doc("Item Tax Template",c_row.item_tax_template)
						for tax_row in tax_temp_obj.taxes:

							gst_s = frappe.get_single("GST Settings")

							for gst_row in gst_s.gst_accounts:
								if gst_row.cgst_account == tax_row.tax_type:
									cgst = tax_row.tax_rate
								elif gst_row.sgst_account == tax_row.tax_type:
									sgst = tax_row.tax_rate
								elif gst_row.igst_account == tax_row.tax_type:
									igst = tax_row.tax_rate
								elif gst_row.cess_account == tax_row.tax_type:
									cess = tax_row.tax_rate
				data2 = {}
				data2['challan_number'] = se_doc.name
				data2['challan_date'] = se_doc.posting_date
				data2['types_of_goods'] = "Inputs"
				supp_details = frappe.db.sql(""" select adds.gstin as gstin_of_job_worker,
												concat(adds.gst_state_number,'-',adds.gst_state ) as state,
											 CASE
											 When supp.gst_category != "SEZ"
											 Then "Non-SEZ"
											 Else "SEZ"
											 End as job_workers_type
												from `tabSupplier` supp
												INNER JOIN `tabDynamic Link` dl
												on dl.link_name = supp.name
												INNER JOIN `tabAddress` adds
												on dl.parent = adds.name
												where supp.name = %(supp)s """, {'supp':po_doc.supplier}, as_dict=1)
				if supp_details:
					dic2 = supp_details[0]
					for key,value in dic2.items():
						data2[key] = value
				else:
					frappe.throw("Supplier Address Should Be There")

				data2['description_of_goods']=row.description
				data2['unique_quantity_code'] = row.stock_uom
				data2['quantity'] = row.transfer_qty
				data2['taxable_value'] = row.basic_amount
				data2['integrated_tax_rate'] = igst if igst else 0
				data2['central_tax_rate'] = cgst if cgst else 0
				data2['state_ut_tax_rate'] = sgst if sgst else 0
				data2['cess'] = cess if cess else 0
				data.append(data2)
		return data

	if filters.report == "ITC-05 A":
		data = []
		s_d = "'" + conditions['start_date'] + "'"
		m_d = "'" + conditions['end_date'] + "'"
		query = """ select pr.name as pr_name, po.name as po_name, se.name as se_name
					from `tabPurchase Receipt` pr
					Inner Join `tabPurchase Receipt Item` pri on pr.name = pri.parent
					Inner Join `tabPurchase Order` po on pri.purchase_order = po.name
					Inner join `tabStock Entry` se on po.name = se.purchase_order
					where
					pr.docstatus = 1 and se.stock_entry_type = "Send to Subcontractor" and
					pr.posting_date between {0} and {1}
					and pr.company = '{2}' """.format(s_d, m_d, filters.get('company'))

		if filters.get('company_address'):
			query+= """ and po.billing_address = '{0}' """.format(filters.get('company_address'))

		pr = frappe.db.sql(query,as_dict=1)
		for name in pr:
			print("pr----------------------------------------", name)
			pr_doc = frappe.get_doc("Purchase Receipt", name.pr_name)
			dist_pr_batch = frappe.db.sql(""" select distinct(batch_no) as batch_no
											   from `tabPurchase Receipt Item Supplied`
			 								   where parent = '{0}' and qty_to_be_consumed = 0 """.format(name.pr_name),as_dict=1)
			print("-------------------dist_pr_batch",dist_pr_batch)
			se_doc = frappe.get_doc("Stock Entry", name.se_name)
			se_doc_batch_count = 0
			for res in dist_pr_batch:
				if res['batch_no']:
					se_doc = frappe.get_doc("Stock Entry",name.se_name)
					se_batch_count = frappe.db.sql(""" select count(*) as total from `tabStock Entry Detail`
															where parent = '{0}' 
															and batch_no = '{1}' """.format(name.se_name,res['batch_no']),as_dict=1)
					se_doc_batch_count += se_batch_count[0]['total']
					print("--------------------------se_doc_batch_count",se_batch_count)
			if se_doc_batch_count == 0:
				for row in pr_doc.items:
					if row.is_subcontracted == "Yes":
						global jw_challan_number, jw_challan_date, nature_of_job_work_done
						jw_challan_number = row.challan_number_issues_by_job_worker
						jw_challan_date = row.challan_date_issues_by_job_worker
						nature_of_job_work_done = row.nature_of_job_work_done
						break

				for row in pr_doc.supplied_items:
					if row.qty_to_be_consumed > 0:
						data2 = {}
						if name.po_name:
							po_doc = frappe.get_doc("Purchase Order",name.po_name)
							data2['original_challan_number_issued_by_principal'] = se_doc.name
							data2['original_challan_date_issued_by_principal'] = se_doc.posting_date
						data2['challan_number_issued_by_job_worker'] = jw_challan_number if jw_challan_number else ""
						data2['challan_date_issued_by_job_worker'] = jw_challan_date if jw_challan_date else ""
						supp_details = frappe.db.sql(""" select adds.gstin as gstin_of_job_worker,
														adds.state as state, supp.gst_category as job_workers_type
														from `tabSupplier` supp
														INNER JOIN `tabDynamic Link` dl
														on dl.link_name = supp.name
														INNER JOIN `tabAddress` adds
														on dl.parent = adds.name
														where supp.name = %(supp)s """,
													 {'supp': pr_doc.supplier}, as_dict=1)
						dic2 = supp_details[0]
						for key, value in dic2.items():
							data2[key] = value

						rm_item_obj = frappe.get_doc("Item", row.rm_item_code)
						data2['description_of_goods'] = rm_item_obj.description
						data2['unique_quantity_code'] = row.stock_uom
						data2['quantity'] = row.qty_to_be_consumed
						data2['losses_uqc'] = row.stock_uom
						data2['losses_quantity'] = row.loss_qty
						data2['nature_of_job_work_done'] = nature_of_job_work_done
						data.append(data2)
		return data
	elif filters.report == "ITC-05 B" or filters.report == "ITC-05 C":	
		pass
# def get_conditions(filters):
# 	conditions = {}
# 	if filters.gstin_of_manufacturer:
# 		conditions['gstin_of_manufacturer'] = filters.gstin_of_manufacturer
# 	return conditions



@frappe.whitelist()
def get_json(filters, report_name, data):
	filters = json.loads(filters)
	report_data = json.loads(data)
	# gstin = get_company_gstin_number(filters.get("company"), filters.get("company_address"))

	# fp = "%02d%s" % (getdate(filters["to_date"]).month, getdate(filters["to_date"]).year)
	#
	# gst_json = {"version": "GST3.0.4",
	# 	"hash": "hash", "gstin": gstin, "fp": fp}

	# res = {}

	
	return {
		'report_name': report_name,
		'report': filters['report'],
		'data': report_data
	}



@frappe.whitelist()
def download_json_file():
	''' download json content in a file '''
	data = frappe._dict(frappe.local.form_dict)
	frappe.response['filename'] = frappe.scrub("{0} {1}".format(data['report_name'], data['report'])) + '.json'
	frappe.response['filecontent'] = data['data']
	frappe.response['content_type'] = 'application/json'
	frappe.response['type'] = 'download'
