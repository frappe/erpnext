# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


def execute(filters=None):
	columns=get_columns(filters)
	data = get_data(filters)
	return columns,data


def get_columns(filters):
	columns=[
			{
				"label": _("Company"),
				"fieldname":"company",
				"fieldtype":"Link",
				"options":"Company",
				"width": 140
			},
			{
				"label": _("Month"),
				"fieldname": "month",
				"fieldtype": "Data",
				"width": 140
			},
			{
				"label": _("Year"),
				"fieldname": "year",
				"fieldtype": "Data",
				"width": 140
			},
			{
				"label": _("No. Of Invoices"),
				"fieldname": 'no_of_invoices',
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("Purchase Amount"),
				"fieldname": 'total',
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("Exempted Purchase"),
				"fieldname": 'exempted_purchase',
				"fieldtype": "Data",
				"width": 100
			},

			{
				"label": _("Taxable Purchase"),
				"fieldname": 'taxable_purchase',
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("Local Tax"),
				"fieldname": 'local_tax',
				"fieldtype": "Data",
				"width": 100
			},

			{
				"label": _("Taxcable Import"),
				"fieldname": 'taxcable_import',
				"fieldtype": "Float",
				"width": 100
			},
			{
				"label": _("Import Tax"),
				"fieldname": 'import_tax',
				"fieldtype": "Float",
				"width": 100
			},
			{
				"label": _("Capital Purchase"),
				"fieldname": 'capital_purchase',
				"fieldtype": "Float",
				"width": 100
			},
			{
				"label": _("Capital Tax"),
				"fieldname": 'capital_tax',
				"fieldtype": "Float",
				"width": 100
			}
			
			
		
	]
	return columns

def get_condition(filters):

	conditions=" "
	if filters.get("year"):
		conditions += " AND year(si.posting_date)='%s'" % filters.get('year')
	if filters.get("company"):
		conditions += " AND si.company='%s'" % filters.get('company')
	return conditions

def get_data(filters):
	conditions = get_condition(filters)
	doc = frappe.db.sql("""select
		company,
		monthname(posting_date) as month,
		year(posting_date) as year,
		count(si.name) as no_of_invoices,
		case  when si.country = "Nepal" then
		(ifnull((select sum(grand_total) from `tabPurchase Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
		and xsi.total_taxes_and_charges=0 and year(xsi.posting_date)=year(si.posting_date) and si.company=xsi.company and xsi.docstatus=1 group by month(xsi.posting_date) desc, year(xsi.posting_date)
		), 0) + ifnull((select sum(total) from `tabPurchase Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
		and xsi.total_taxes_and_charges != 0 and xsi.docstatus=1 and year(xsi.posting_date)=year(si.posting_date) and si.company=xsi.company group by month(xsi.posting_date) desc, year(xsi.posting_date)
		), 0) + ifnull( (select sum(xsi.total) from`tabPurchase Invoice` as xsi where xsi.country != "Nepal" and year(xsi.posting_date)=year(si.posting_date) 
		and si.company=xsi.company and month(xsi.posting_date)=month(si.posting_date) and xsi.docstatus=1 group by month(xsi.posting_date) desc, year(xsi.posting_date)),0)
		+ifnull((select sum(pii.amount) from `tabPurchase Invoice` as pd 
		inner join `tabPurchase Invoice Item` as pii on pd.name=pii.parent 
		where  month(pd.posting_date)= month(si.posting_date) and year(pd.posting_date)=year(si.posting_date) and pd.docstatus=1
		and pii.is_fixed_asset=1 and si.company=pd.company  group by month(pd.posting_date) desc, year(pd.posting_date)),0)) 
		
		when si.country!= "Nepal" then
		(ifnull((select sum(base_grand_total) from `tabPurchase Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
		and xsi.total_taxes_and_charges=0 and year(xsi.posting_date)=year(si.posting_date) and si.company=xsi.company and xsi.docstatus=1 group by month(xsi.posting_date) desc, year(xsi.posting_date)
		), 0) + ifnull((select sum(base_total) from `tabPurchase Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
		and xsi.base_total_taxes_and_charges != 0 and year(xsi.posting_date)=year(si.posting_date) and xsi.docstatus=1 and si.company=xsi.company group by month(xsi.posting_date) desc, year(xsi.posting_date)
		), 0) + ifnull( (select sum(xsi.total) from`tabPurchase Invoice` as xsi where xsi.country != "Nepal" and year(xsi.posting_date)=year(si.posting_date) 
		and si.company=xsi.company and month(xsi.posting_date)=month(si.posting_date) and xsi.docstatus=1 group by month(xsi.posting_date) desc, year(xsi.posting_date)),0)
		+ifnull((select sum(pii.base_amount) from `tabPurchase Invoice` as pd 
		inner join `tabPurchase Invoice Item` as pii on pd.name=pii.parent 
		where  month(pd.posting_date)= month(si.posting_date) and year(pd.posting_date)=year(si.posting_date) 
		and pii.is_fixed_asset=1 and si.company=pd.company and pd.docstatus=1 group by month(pd.posting_date) desc, year(pd.posting_date)),0)) 
		end as total,

		case  when si.country = "Nepal" then
		(select sum(xsi.grand_total) from `tabPurchase Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
			and xsi.total_taxes_and_charges=0 and year(xsi.posting_date)=year(si.posting_date) and si.company=xsi.company and xsi.docstatus=1 group by month(xsi.posting_date) desc, year(xsi.posting_date)
			)
		
		when si.country != "Nepal" then
		(select sum(xsi.base_grand_total) from `tabPurchase Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
			and xsi.base_total_taxes_and_charges=0 and year(xsi.posting_date)=year(si.posting_date) and si.company=xsi.company and xsi.docstatus=1  group by month(xsi.posting_date) desc, year(xsi.posting_date))
		End as exempted_purchase,

		case  when si.country != "Nepal" then
		(select sum(xsi.base_total) from `tabPurchase Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
			and xsi.base_total_taxes_and_charges != 0 and year(xsi.posting_date)=year(si.posting_date) and si.company=xsi.company  and xsi.docstatus=1 group by month(xsi.posting_date) desc, year(xsi.posting_date)) 
		

		when si.country = "Nepal" then
		(select sum(xsi.total) from `tabPurchase Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
			and xsi.total_taxes_and_charges != 0 and year(xsi.posting_date)=year(si.posting_date) and si.company=xsi.company and xsi.docstatus=1 group by month(xsi.posting_date) desc, year(xsi.posting_date)) 
		End as taxable_purchase,

		case  when si.country = "Nepal" then
		(select sum(xsi.total_taxes_and_charges) from `tabPurchase Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
			and xsi.total_taxes_and_charges != 0 and year(xsi.posting_date)=year(si.posting_date) and si.company=xsi.company and xsi.docstatus=1  group by month(xsi.posting_date) desc, year(xsi.posting_date)
			) 
		

		when si.country != "Nepal" then
		((select sum(xsi.base_total_taxes_and_charges) from `tabPurchase Invoice` as xsi where month(xsi.posting_date)=month(si.posting_date)
			and xsi.base_total_taxes_and_charges != 0 and year(xsi.posting_date)=year(si.posting_date) and si.company=xsi.company and xsi.docstatus=1 group by month(xsi.posting_date) desc, year(xsi.posting_date)
			))
		End as local_tax,

		case  when si.country = "Nepal" then
		(select sum(xsi.total) from`tabPurchase Invoice` as xsi where xsi.country!= "Nepal" and year(xsi.posting_date)=year(si.posting_date) 
		and si.company=xsi.company and month(xsi.posting_date)=month(si.posting_date) and xsi.docstatus=1 group by month(xsi.posting_date) desc, year(xsi.posting_date)) 
		

		when si.country != "Nepal" then
		(select sum(xsi.base_total) from`tabPurchase Invoice` as xsi where xsi.country != "Nepal" and year(xsi.posting_date)=year(si.posting_date) 
		and si.company=xsi.company and month(xsi.posting_date)=month(si.posting_date) and xsi.docstatus=1 group by month(xsi.posting_date) desc, year(xsi.posting_date)) 
		End as taxcable_import,

		case  when si.country = "Nepal" then
		(select sum(xsi.total_taxes_and_charges) from `tabPurchase Invoice` as xsi where xsi.country = "Nepal" and year(xsi.posting_date)=year(si.posting_date) 
		and si.company=xsi.company and month(xsi.posting_date)=month(si.posting_date) and xsi.docstatus=1 group by month(xsi.posting_date) desc, year(xsi.posting_date) )
		

		when si.country != "Nepal" then
		(select sum(xsi.base_total_taxes_and_charges) from `tabPurchase Invoice` as xsi where xsi.country != "Nepal" and year(xsi.posting_date)=year(si.posting_date) 
		and si.company=xsi.company and month(xsi.posting_date)=month(si.posting_date) and xsi.docstatus=1 group by month(xsi.posting_date) desc, year(xsi.posting_date) )
		End as import_tax,

		case  when si.country = "Nepal" then
		(select sum(pii.base_amount) from `tabPurchase Invoice` as pd 
		inner join `tabPurchase Invoice Item` as pii on pd.name=pii.parent 
		where  month(pd.posting_date)= month(si.posting_date) and year(pd.posting_date)=year(si.posting_date) 
		and pii.is_fixed_asset=1 and pd.docstatus=1 and si.company=pd.company group by month(pd.posting_date) desc, year(pd.posting_date))

		when si.country != "Nepal" then
		(select sum(pii.amount) from `tabPurchase Invoice` as pd 
		inner join `tabPurchase Invoice Item` as pii on pd.name=pii.parent 
		where  month(pd.posting_date)= month(si.posting_date) and year(pd.posting_date)=year(si.posting_date) 
		and pii.is_fixed_asset=1 and pd.docstatus=1 and si.company=pd.company  group by month(pd.posting_date) desc, year(pd.posting_date))
		End as capital_purchase,

		case  when si.country = "Nepal" then
		(select sum(pii.amount)*13/100 from `tabPurchase Invoice Item` as pii  
		inner join `tabPurchase Invoice` as pd on pd.name=pii.parent 
		where month(pd.posting_date)=month(si.posting_date) and year(pd.posting_date)=year(si.posting_date)
		and pii.is_fixed_asset=1 and pd.docstatus=1 and si.company=pd.company group by month(pd.posting_date) desc, year(pd.posting_date)) 

		when si.country != "Nepal" then
		(select sum(pii.base_amount)*13/100 from `tabPurchase Invoice Item` as pii  
		inner join `tabPurchase Invoice` as pd on pd.name=pii.parent 
		where month(pd.posting_date)=month(si.posting_date) and year(pd.posting_date)=year(si.posting_date)
		and pii.is_fixed_asset=1 and pd.docstatus=1   and si.company=pd.company group by month(pd.posting_date) desc, year(pd.posting_date)) 
		End as capital_tax
		from
		`tabPurchase Invoice` as si
		where si.docstatus=1 {conditions}
		group by year(si.posting_date) desc,
		monthname(si.posting_date) asc,
		company""".format(conditions=conditions),filters, as_dict=1)
	print(doc)
	return doc
