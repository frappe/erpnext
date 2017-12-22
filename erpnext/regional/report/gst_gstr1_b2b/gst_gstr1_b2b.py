# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import msgprint, _

def execute(filters=None):

	gstAcc = {"igst":filters.pop("igst",None),
	          "sgst":filters.pop("sgst",None),
			  "cgst":filters.pop("cgst",None)}
	cess = filters.pop("cess",None)
	if cess == None or gstAcc["igst"] == None or gstAcc["sgst"] == None or gstAcc["cgst"] == None:
		return [0,0,0,0,0,0,0,0,0,0,0]

	return _execute(filters,gstAcc,cess)

def _execute(filters,gstAcc=None,cess=None, additional_table_columns=None, additional_query_columns=None):

	data = []
	if not filters: filters = frappe._dict({})



	invoice_list = get_invoices(filters, additional_query_columns)

	columns = get_columns(invoice_list, additional_table_columns)

	invoice_num = []
	invoice_dict = {}
	invoice_map = {}
	for i in invoice_list:

		pos = frappe.db.sql("""select gst_state,gst_state_number from `tabAddress` as ta join
		                      `tabSales Invoice` as tsi on  tsi.shipping_address_name = ta.name
							  where tsi.name = {0}
		                    """.format("\""+i.name+"\""),(),as_dict=1)
		placeOfSupply=""
		for ps in pos:
			placeOfSupply = "{0:02d}-{1}".format(ps["gst_state_number"],ps["gst_state"])
		invoice_num.append(i.name)
		invoice_map[i.name] = {"invoice_val":i.base_rounded_total}
		invoice_dict[i.name] = {"gstin":i.customer_gstin,
								 "name":i.name,
								 "date":i.posting_date,
								 "invoice_value":i.base_grand_total,
								 "place_of_supply":placeOfSupply,#i.place_of_supply,
								 "reverse_charge":i.reverse_charge,
								 "invoice_type":i.invoice_type,
								 "ecommerce_gstin":i.ecommerce_gstin,
								 "base_net_total":i.base_net_total
								 }

	if len(invoice_num) != 0:
		invoice_tax_map = get_invoice_tax_map(invoice_num,gstAcc,cess,invoice_map)


		for inv in invoice_tax_map.keys():
			invoice = inv

			for tax_rate in invoice_tax_map[inv]:
				datum = []
				if tax_rate != 0:
				#item_code = itm_cd
					
					if invoice_tax_map[inv][tax_rate]["tax_rate"] != 0:
						datum = [invoice_dict[inv]["gstin"],
				         		invoice_dict[inv]["name"],
						 		invoice_dict[inv]["date"],
						 		invoice_dict[inv]["invoice_value"],
						 		invoice_dict[inv]["place_of_supply"],
						 		invoice_dict[inv]["reverse_charge"],
						 		invoice_dict[inv]["invoice_type"],
						 		invoice_dict[inv]["ecommerce_gstin"]

						 		]


						datum =datum+[invoice_tax_map[inv][tax_rate]["tax_rate"],invoice_tax_map[inv][tax_rate]["inv_value"],invoice_tax_map[inv][tax_rate]["cess"]]
						data.append(datum)

	return columns, data

def get_columns(invoice_list, additional_table_columns):
	"""return columns based on filters"""
	columns = [
		_("GSTIN")+"::120",
		_("Invoice") + ":Link/Sales Invoice:120",
		_("Posting Date") + ":Date:80",
		_("Invoice Value")+":Currency/currency:120",
		_("Place of Supply")+":Data:120",
		_("Reverse Charge")+":Data:10",
		_("Invoice Type")+":Data:120",
		_("E-Commerce GSTIN")+"::120",
		_("Rate")+"::120",
		_("Taxable Value")+":Currency/currency:120",
		_("Cess Amount")+":Currency/currency:120"


	]

	if additional_table_columns:
		columns += additional_table_columns

	return columns



def get_conditions(filters):
	conditions = ""

	if filters.get("company"): conditions += " and company=%(company)s"
	if filters.get("customer"): conditions += " and customer = %(customer)s"

	if filters.get("from_date"): conditions += " and posting_date >= %(from_date)s"
	if filters.get("to_date"): conditions += " and posting_date <= %(to_date)s"

	if filters.get("mode_of_payment"):
		conditions += """ and exists(select name from `tabSales Invoice Payment`
			 where parent=`tabSales Invoice`.name
			 	and ifnull(`tabSales Invoice Payment`.mode_of_payment, '') = %(mode_of_payment)s)"""

	return conditions

def get_invoices(filters, additional_query_columns):

	if additional_query_columns:
		additional_query_columns = ', ' + ', '.join(additional_query_columns)


	conditions = get_conditions(filters)
	return frappe.db.sql("""select name,customer_gstin, posting_date, place_of_supply,reverse_charge,invoice_type,ecommerce_gstin,
                        debit_to, project, customer, customer_name, remarks,
		base_net_total, base_grand_total, base_rounded_total, outstanding_amount {0}
		from `tabSales Invoice`
		where docstatus = 1 and customer_gstin<>"NA" %s order by posting_date desc, name desc""".format(additional_query_columns or '') %
		conditions, filters, as_dict=1)

def get_invoice_income_map(invoice_list):
	income_details = frappe.db.sql("""select parent, income_account, sum(base_net_amount) as amount
		from `tabSales Invoice Item` where parent in (%s) group by parent, income_account""" %
		', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]))

	invoice_income_map = {}
	for d in income_details:
		invoice_income_map.setdefault(d.parent, frappe._dict()).setdefault(d.income_account, [])
		invoice_income_map[d.parent][d.income_account] = flt(d.amount)

	return invoice_income_map

def get_invoice_tax_map(invoice_list,gstAcc,cess,invMap):
	data = {} # structure data{inv:{rate:{tax_rate:rate,inv value:value,tax:tax}}}
	gst_t_accs = "\""+gstAcc["igst"]+"\",\""+gstAcc["cgst"]+"\","+"\""+gstAcc["sgst"]+"\""
	cess_t = "\""+cess+"\""

	#get list of invoice with GST In no
	invoice_list1 = frappe.db.sql(""" select name from `tabSales Invoice` where
				   name in (%s) """%', '.join(["%s"]*len(invoice_list)),
				   tuple([inv for inv in invoice_list]),as_list=1
				   )

	#get the items in the sales invoice_list
	sales_invoice_items = frappe.db.sql("""select parent,item_code,amount from `tabSales Invoice Item`
	                      where parent in (%s) """%', '.join(["%s"]*len(invoice_list)),
						  tuple([inv for inv in invoice_list]), as_dict=1
						  )
	item_inv_map = {}
	item_tax_map = {}
	item_inv_price_map = {}
	itm_cds=[]
	for sii in sales_invoice_items:
		if sii["parent"] not in item_inv_map:
			item_inv_map[sii["parent"]] = [sii.item_code]
		else:
			item_inv_map[sii["parent"]].append(sii.item_code)
		if sii["item_code"] not in itm_cds:
			itm_cds.append(sii["item_code"])
			item_tax_map[sii["item_code"]] = {}
			for accs in gstAcc.keys():
				item_tax_map[sii["item_code"]][gstAcc[accs]] = None
		if sii["parent"] not in item_inv_price_map:
			item_inv_price_map[sii["parent"]] = {sii["item_code"]:sii.amount}
		else:
			if sii["item_code"] in item_inv_price_map[sii["parent"]]:
				amt = item_inv_price_map[sii["parent"]][sii["item_code"]]
				amt+=sii["item_code"]
				item_inv_price_map[sii["parent"]][sii["item_code"]]= amt
			else:
				item_inv_price_map[sii["parent"]][sii["item_code"]]=sii["amount"]


	item_tax = frappe.db.sql("""select parent as invoice,item_code,item_tax_rate from `tabSales Invoice Item`
	 						    where parent in (%s) """%', '.join(["%s"]*len(invoice_list)),
								tuple([itmc for itmc in invoice_list]),as_dict=1)



	#get the account heads, rates in the invoice_list
	item_tax_map = {}
	for itm in item_tax:
		if (itm["invoice"] not in item_tax_map) :
			item_tax_map[itm["invoice"]] = {}
		if (itm["item_code"] not in item_tax_map[itm["invoice"]]):
			item_tax_map[itm["invoice"]][itm["item_code"]] = {}
		tax_str = itm["item_tax_rate"][1:-1]
		tax_list = tax_str.split(",")
		tax_rate_dict = {}
		for tl in tax_list:


			if tl!="" :
				tlKey,tlVal = tl.split(":")
				tax_rate_dict[tlKey[1:-1].replace("\"","")] = float(tlVal)
		item_tax_map[itm["invoice"]][itm["item_code"]] = tax_rate_dict


	inv_tax_map= {} #structure inv_tax_map{inv:{tax_head:rate}}


	inv_tax = frappe.db.sql("""select parent as sales_inv,account_head,rate as tax_rate from `tabSales Taxes and Charges`
							where parent in (%s) and account_head in ({0})
	                        """.format(gst_t_accs)%', '.join(["%s"]*len(invoice_list)),
							tuple([inv for inv in invoice_list]),as_dict=1
							)

	for inv in invoice_list:

		inv_tax_map[inv] = {}
		if inv not in data:
			data[inv] = {}
	for itm in inv_tax:

		inv_tax_map[itm.sales_inv].update({itm.account_head:itm.tax_rate})
		if itm.tax_rate not in data[itm.sales_inv] :
			data[itm.sales_inv][itm.tax_rate] = {"tax_rate":0,"inv_value":0,"tax":0,"cess":0}


	#get cess
	sales_invoice_cess = frappe.db.sql("""select parent as sales_inv,account_head,tax_amount from `tabSales Taxes and Charges`
									   where parent in (%s) and account_head in ({0})
									   """.format(cess_t)%', '.join(["%s"]*len(invoice_list)),
		   							tuple([inv for inv in invoice_list]),as_dict=1
		   							)
	inv_cess_map = {}
	for sic in sales_invoice_cess:
		inv_cess_map[sic.sales_inv] = sic["tax_amount"]

	# fill in the default Data
	for inv in invoice_list:
		tax_type = inv_tax_map[inv]

		cVal = 0
		if inv in inv_cess_map:
			cVal = inv_cess_map[inv]
		for itm in item_inv_map[inv]:
			itax = 0
			itaxRate = 0

			#check if the item has a default tax defined for the tax in the sales invoice_num
			#if the tax rate is defined then take that tax rate otherwise take the default from the Order
			for tax_acc in inv_tax_map[inv]:

				if tax_acc.strip() in item_tax_map[inv][itm].keys():
				#and item_tax_map[inv][itm][tax_acc] != None:

					itaxRate+= item_tax_map[inv][itm][tax_acc]


				else:
					itaxRate+=inv_tax_map[inv][tax_acc]

			itax = float(itaxRate*float(item_inv_price_map[inv][itm]))
			currRate = itaxRate
			#invVal= invMap[inv]["invoice_val"]
			invVal=float(item_inv_price_map[inv][itm])
			currTax = 0.0
			if itaxRate in data[inv]:
				#currRate,invVal,currTax = data[inv][itaxRate]
				currRate = data[inv][itaxRate]["tax_rate"]
				invVal+= data[inv][itaxRate]["inv_value"]

			currTax=currTax+itax
			data[inv][currRate]={"tax_rate":currRate,"inv_value":invVal,"tax":float(currTax),"cess":cVal}

			#update the data

	#for inv in invoice_list:


	return data

def get_invoice_so_dn_map(invoice_list):
	si_items = frappe.db.sql("""select parent, sales_order, delivery_note, so_detail
		from `tabSales Invoice Item` where parent in (%s)
		and (ifnull(sales_order, '') != '' or ifnull(delivery_note, '') != '')""" %
		', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]), as_dict=1)

	invoice_so_dn_map = {}
	for d in si_items:
		if d.sales_order:
			invoice_so_dn_map.setdefault(d.parent, frappe._dict()).setdefault(
				"sales_order", []).append(d.sales_order)

		delivery_note_list = None
		if d.delivery_note:
			delivery_note_list = [d.delivery_note]
		elif d.sales_order:
			delivery_note_list = frappe.db.sql_list("""select distinct parent from `tabDelivery Note Item`
				where docstatus=1 and so_detail=%s""", d.so_detail)

		if delivery_note_list:
			invoice_so_dn_map.setdefault(d.parent, frappe._dict()).setdefault("delivery_note", delivery_note_list)

	return invoice_so_dn_map

def get_customer_details(customers):
	customer_map = {}
	for cust in frappe.db.sql("""select name, territory, customer_group from `tabCustomer`
		where name in (%s)""" % ", ".join(["%s"]*len(customers)), tuple(customers), as_dict=1):
			customer_map.setdefault(cust.name, cust)

	return customer_map


def get_mode_of_payments(invoice_list):
	mode_of_payments = {}
	if invoice_list:
		inv_mop = frappe.db.sql("""select parent, mode_of_payment
			from `tabSales Invoice Payment` where parent in (%s) group by parent, mode_of_payment""" %
			', '.join(['%s']*len(invoice_list)), tuple(invoice_list), as_dict=1)

		for d in inv_mop:
			mode_of_payments.setdefault(d.parent, []).append(d.mode_of_payment)

	return mode_of_payments
