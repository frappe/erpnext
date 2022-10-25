# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	
	from_date = filters.get('from_date')
	to_date = filters.get('to_date')
	customer_group = filters.get('customer_group')
	customer_name = filters.get('customer_name')
    
	condition = ''
	if not filters:
		filters = {}

	if filters.get('customer_group'):
		condition += " and DN.customer_group = '{0}'".format(filters.customer_group)
	
	if filters.get('customer_name'):
		condition += " and DN.customer = '{0}'".format(filters.customer_name)

	columns = [
		("Company") + "::120",
		("DN Number") + ":Link/Delivery Note:100",
		("Customer") + ":Link/Delivery Note:120",
		("Customer Name") + "::120",
		("DN Qty") + "::120",
		("Territory") + "::120",
		("Customer Group") + "::120",
		("Driver") + "::120",
		("Phone No") + "::120",
		("Vehicle Number") + "::120",
        ("Supplier") + "::150",
		 ("Supplier Name") + "::150",
        ("Gate In") + "::120",
        ("Gate Out") + "::120",
        ("First Weight") + "::120",
        ("Second Weight") + "::150",
        ("Net Weight") + "::120",
        ("DN Total Net Weight") + "::120",
        ("Differnce") + "::150",
        ("Sale Invoice") + "::150",
        ("Freight Amount") + "::150",
        ("Freight Per Pet") + "::120",
    ]
	
	data = []
	data = frappe.db.sql("""
	Select 
		DN.company as company,
		DN.name as dn_number,
		DN.customer as customer,
		DN.customer_name as customer_name,
		DN.total_qty as dn_qty,
		DN.territory as territory,
		DN.customer_group as customer_group,
		GPIN.driver as driver,
		GPIN.phone_no as phone_no,
		GPIN.vehicle as vehicle_number,
		GPIN.supplier as supplier,
		SU.supplier_name as supplier_name,
		GPIN.name as gate_in,
		GPOUT.name as gate_out,
		GPIN.first_weight as first_weight,
		GPOUT.second_weight as second_weight,
		GPOUT.net_weight as net_weight,
		DN.total_net_weight as dn_total_net_weight,
		GPOUT.net_weight - DN.total_net_weight as differnce,
		SII.parent as sale_invoice,
		IF(STC.tax_amount < 0, -1 * STC.tax_amount, 0) as freight_amount,
		IF(STC.tax_amount < 0, -1 * STC.tax_amount/DN.total_qty,0) as freight_per_pet
		from `tabDelivery Note` DN
		LEFT JOIN `tabGate Pass` GPIN ON 
			DN.reference_gate_pass = GPIN.name
		LEFT JOIN `tabGate Pass` GPOUT ON 
			GPIN.name = GPOUT.reference_gate_pass and GPOUT.type = 'OUT'
		LEFT JOIN `tabSupplier` SU ON 
			SU.name = GPIN.supplier
		LEFT OUTER JOIN `tabSales Invoice Item` as SII ON 
			DN.name = SII.delivery_note
		LEFT JOIN `tabSales Taxes and Charges` as STC ON 
			STC.parent = SII.parent and charge_type ='Actual'
		where  DN.docstatus = 1
		and DN.is_return = 'No'
		and DN.posting_date between '{from_date}'  and '{to_date}' {condition} group by DN.name
	
	""".format(from_date=from_date, to_date=to_date,condition=condition), as_dict=True)
	
	return columns, data
