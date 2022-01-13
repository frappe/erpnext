# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

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
				"fieldtype": "Data",
				"fieldname": "challan_number",
				"width": 140
			},
			{
				"label": _("Challan Date"),
				"fieldtype": "Data",
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
				"fieldtype": "Data",
				"fieldname": "quantity",
				"width": 140
			},
			# {
			# 	"label": _("Taxable Value"),
			# 	"fieldtype": "Data",
			# 	"fieldname": "taxable_value",
			# 	"width": 100
			# },
			# {
			# 	"label": _("Integrated Tax Rate In(%)"),
			# 	"fieldtype": "Data",
			# 	"fieldname": "integrated_tax_rate",
			# 	"width": 100
			# },
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
				"fieldtype": "Data",
				"fieldname": "original_challan_number_issued_by_principal",
				"width": 140
			},
			{
				"label": _("Original Challan Date Issued by Principal"),
				"fieldtype": "Data",
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
				"fieldtype": "Data",
				"fieldname": "challan_date_issued_by_job_worker",
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
				"fieldtype": "Data",
				"fieldname": "quantity",
				"width": 140
			},
			# {
			# 	"label": _("Taxable Value"),
			# 	"fieldtype": "Data",
			# 	"fieldname": "taxable_value",
			# 	"width": 100
			# },
			# {
			# 	"label": _("Integrated Tax Rate In(%)"),
			# 	"fieldtype": "Data",
			# 	"fieldname": "integrated_tax_rate",
			# 	"width": 100
			# },
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
def get_data(filters):
	if filters.report == "ITC-04":
		data = []

		se = frappe.db.get_all("Stock Entry",fields=['name'],filters={'docstatus':['=',1],'stock_entry_type':['=',"Send to Subcontractor"]})
		for name in se:
			se_doc = frappe.get_doc("Stock Entry",name.name)
			po_doc = frappe.get_doc("Purchase Order",se_doc.purchase_order)
			for row in se_doc.items:
				data2 = {}
				data2['challan_number'] = se_doc.name
				data2['challan_date'] = se_doc.posting_date
				data2['types_of_goods'] = "Inputs"
				supp_details = frappe.db.sql(""" select adds.gstin as gstin_of_job_worker,
												adds.state as state , supp.gst_category as job_workers_type
												from `tabSupplier` supp
												INNER JOIN `tabDynamic Link` dl
												on dl.link_name = supp.name
												INNER JOIN `tabAddress` adds
												on dl.parent = adds.name
												where supp.name = %(supp)s """,{'supp':po_doc.supplier},as_dict=1)
				dic2 = supp_details[0]
				for key,value in dic2.items():
					data2[key] = value

				data2['description_of_goods']=row.description
				data2['unique_quantity_code'] = row.stock_uom
				data2['quantity'] = row.transfer_qty

				data.append(data2)
		return data

	elif filters.report == "ITC-05 A":
		data = []
		pr = frappe.db.get_all("Purchase Receipt", fields=['name'],
							   filters={'docstatus': ['=', 1]})

		for name in pr:
			pr_doc = frappe.get_doc("Purchase Receipt", name.name)

			for row in pr_doc.items:
				global po_name
				po_name = row.purchase_order
				break

			for row in pr_doc.supplied_items:
				data2 = {}
				if po_name:
					po_doc = frappe.get_doc("Purchase Order",po_name)
					data2['original_challan_number_issued_by_principal'] = po_doc.name
					data2['original_challan_date_issued_by_principal'] = po_doc.transaction_date
				data2['challan_number_issued_by_job_worker'] = pr_doc.name
				data2['challan_date_issued_by_job_worker'] = pr_doc.posting_date
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
				data2['quantity'] = row.consumed_qty
				data.append(data2)
		return data

def get_conditions(filters):
	conditions = {}
	if filters.gstin_of_manufacturer:
		conditions['gstin_of_manufacturer'] = filters.gstin_of_manufacturer
	return conditions
