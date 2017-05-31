# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate

def execute(filters=None):
	if not filters: filters = {}

	validate_filters(filters)

	columns = get_columns()
	item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_map(filters)

	data = []
	summ_data = [] 
        item_group_prev = ""
        item_group_work = ""
	parent_item_group_prev = ""
        parent_item_group_work = ""
        comp_prev = ""
        comp_curr = ""
        item_count = 0
        tot_open_qty = 0
        tot_in_qty = 0
        tot_out_qty = 0
        tot_open_val = 0
        tot_in_val = 0
        tot_out_val = 0
        tot_bal_qty = 0
	tot_bal_val = 0 
	ptot_open_qty = 0
        ptot_in_qty = 0
        ptot_out_qty = 0
        ptot_open_val = 0
        ptot_in_val = 0
        ptot_out_val = 0
        ptot_bal_qty = 0
	ptot_bal_val = 0    
   
	for (company, parent_item_group, item_group, item) in sorted(iwb_map):
		qty_dict = iwb_map[(company, parent_item_group, item_group, item)]
		data.append([parent_item_group, item_group, item_map[item]["description"], 
			item_map[item]["stock_uom"],
                        qty_dict.opening_qty, qty_dict.opening_rate, qty_dict.opening_val,
			qty_dict.in_qty, qty_dict.in_rate, qty_dict.in_val,
			qty_dict.out_qty, qty_dict.out_rate, qty_dict.out_val,
			qty_dict.bal_qty, qty_dict.val_rate,
			qty_dict.bal_val 
		
		])

	for rows in data:
       		if item_count == 0:
			parent_item_group_prev = rows[0]       			
			item_group_prev = rows[1]
                        tot_open_qty = tot_open_qty + rows[4]
			tot_in_qty = tot_in_qty + rows[7]
			tot_out_qty = tot_out_qty + rows[10]
			tot_open_val = tot_open_val + rows[6]
			tot_in_val = tot_in_val + rows[9]
			tot_out_val = tot_out_val + rows[12]
			tot_bal_qty = tot_bal_qty + rows[13]
			tot_bal_val = tot_bal_val + rows[15]
                        summ_data.append([parent_item_group_prev, item_group_prev, rows[2], 
			 	rows[3], rows[4], rows[5],
				rows[6], rows[7],
				rows[8], rows[9], rows[10],
				rows[11], rows[12], rows[13],
				rows[14], rows[15]			
 				])
                else:
			parent_item_group_work = rows[0]
			item_group_work = rows[1]
			if parent_item_group_prev == parent_item_group_work:
				if item_group_prev == item_group_work:
					item_group_prev = rows[1]
        	                	tot_open_qty = tot_open_qty + rows[4]
					tot_in_qty = tot_in_qty + rows[7]
					tot_out_qty = tot_out_qty + rows[10]
					tot_open_val = tot_open_val + rows[6]
					tot_in_val = tot_in_val + rows[9]
					tot_out_val = tot_out_val + rows[12]
					tot_bal_qty = tot_bal_qty + rows[13]
					tot_bal_val = tot_bal_val + rows[15]
        		                summ_data.append([parent_item_group_prev, item_group_prev, rows[2], 
				 	rows[3], rows[4], rows[5],
					rows[6], rows[7],
					rows[8], rows[9], rows[10],
					rows[11], rows[12], rows[13],
					rows[14], rows[15]			
 					])
				else:
					summ_data.append([parent_item_group_prev, item_group_prev, " ", 
				 	" ", tot_open_qty, 0, tot_open_val,
					tot_in_qty, 0, tot_in_val, tot_out_qty, 0, tot_out_val,
					tot_bal_qty, 0, tot_bal_val				
 					])	
					ptot_open_qty = ptot_open_qty + tot_open_qty 
					ptot_in_qty = ptot_in_qty + tot_in_qty
					ptot_out_qty = ptot_out_qty + tot_out_qty
					ptot_open_val = ptot_open_val + tot_open_val
					ptot_in_val = ptot_in_val + tot_in_val
					ptot_out_val = ptot_out_val + tot_out_val
					ptot_bal_qty = ptot_bal_qty + tot_bal_qty
					ptot_bal_val = ptot_bal_val + tot_bal_val

					summ_data.append([parent_item_group_prev, item_group_work, rows[2], 
				 	rows[3], rows[4], rows[5],
					rows[6], rows[7],
					rows[8], rows[9], rows[10],
					rows[11], rows[12], rows[13],
					rows[14], rows[15]		
 					])
                                
					tot_open_qty = 0
					tot_in_qty = 0
					tot_out_qty = 0
					tot_open_val = 0
				        tot_in_val = 0
				        tot_out_val = 0
					tot_bal_qty = 0
					tot_bal_val = 0
        	                        tot_open_qty = tot_open_qty + rows[4]
					tot_in_qty = tot_in_qty + rows[7]
					tot_out_qty = tot_out_qty + rows[10]
					tot_open_val = tot_open_val + rows[6]
					tot_in_val = tot_in_val + rows[9]
					tot_out_val = tot_out_val + rows[12]
					tot_bal_qty = tot_bal_qty + rows[13]
					tot_bal_val = tot_bal_val + rows[15]
					item_group_prev = item_group_work
                        else:
					summ_data.append([parent_item_group_prev, " ", " ", 
				 	" ", ptot_open_qty, 0, ptot_open_val,
					ptot_in_qty, 0, ptot_in_val, ptot_out_qty, 0, ptot_out_val,
					ptot_bal_qty, 0, ptot_bal_val				
 					])	
					
					summ_data.append([parent_item_group_work, item_group_work, rows[2], 
				 	rows[3], rows[4], rows[5],
					rows[6], rows[7],
					rows[8], rows[9], rows[10],
					rows[11], rows[12], rows[13],
					rows[14], rows[15]		
 					])
                                
					tot_open_qty = 0
					tot_in_qty = 0
					tot_out_qty = 0
					tot_open_val = 0
				        tot_in_val = 0
				        tot_out_val = 0
					tot_bal_qty = 0
					tot_bal_val = 0
					ptot_open_qty = 0
					ptot_in_qty = 0
					ptot_out_qty = 0
					ptot_open_val = 0
				        ptot_in_val = 0
				        ptot_out_val = 0
					ptot_bal_qty = 0
					ptot_bal_val = 0
        	                        tot_open_qty = tot_open_qty + rows[4]
					tot_in_qty = tot_in_qty + rows[7]
					tot_out_qty = tot_out_qty + rows[10]
					tot_open_val = tot_open_val + rows[6]
					tot_in_val = tot_in_val + rows[9]
					tot_out_val = tot_out_val + rows[12]
					tot_bal_qty = tot_bal_qty + rows[13]
					tot_bal_val = tot_bal_val + rows[15]

					item_group_prev = item_group_work
					parent_item_group_prev = parent_item_group_work

		item_count = item_count + 1

        summ_data.append([parent_item_group_prev, " ", " ", 
				 	" ", ptot_open_qty, 0, ptot_open_val,
					ptot_in_qty, 0, ptot_in_val, ptot_out_qty, 0, ptot_out_val,
					ptot_bal_qty, 0, ptot_bal_val				
 					])  
              
		
		
		
		
						
	return columns, summ_data



                   


def get_columns():
	"""return columns"""

	columns = [
		_("Parent Item Group")+"::100",
                _("Item Group")+"::100",
                _("Item Name")+":Link/Item:100",
		_("Stock UOM")+":Link/UOM:90",
		_("Opening Qty")+":Float:100",
                _("Opening Rate")+":Float:100",
		_("Opening Value")+":Float:100",
		_("In Qty")+":Float:80",
		_("In Rate")+":Float:80",
		_("In Value")+":Float:80",
		_("Out Qty")+":Float:80",
		_("Out Rate")+":Float:80",
		_("Out Value")+":Float:80",
		_("Closing Qty")+":Float:100",
		_("Closing Rate")+":Float:90",
                _("Closing Value")+":Float:90",
			]

	return columns

def get_conditions(filters):
	conditions = ""
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if filters.get("to_date"):
		conditions += " and posting_date <= '%s'" % frappe.db.escape(filters["to_date"])
	else:
		frappe.throw(_("'To Date' is required"))

	if filters.get("item_code"):
		conditions += " and item_code = '%s'" % frappe.db.escape(filters.get("item_code"), percent=False)
       
        if filters.get("company"):
		conditions += " and company = '%s'" % frappe.db.escape(filters.get("company"), percent=False)

	if filters.get("warehouse"):
		warehouse_details = frappe.db.get_value("Warehouse", filters.get("warehouse"), ["lft", "rgt"], as_dict=1)
		if warehouse_details:
			conditions += " and exists (select name from `tabWarehouse` wh \
				where wh.lft >= %s and wh.rgt <= %s and sle.warehouse = wh.name)"%(warehouse_details.lft,
				warehouse_details.rgt)

	return conditions

def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""select item.item_group, itemg.parent_item_group, sle.item_code, sle.warehouse, sle.posting_date, sle.actual_qty, sle.valuation_rate,
			sle.company, sle.voucher_type, sle.qty_after_transaction, sle.stock_value_difference, sle.incoming_rate, sle.outgoing_rate
		from `tabStock Ledger Entry` sle, `tabItem` item, `tabItem Group` itemg where sle.docstatus < 2 and sle.item_code = item.name and item.item_group = itemg.item_group_name %s order by sle.posting_date, sle.posting_time, item.item_group, item.name""" %
                conditions, as_dict=1)

def get_item_warehouse_map(filters):
	iwb_map = {}
	from_date = getdate(filters["from_date"])
	to_date = getdate(filters["to_date"])

	sle = get_stock_ledger_entries(filters)

	for d in sle:
                key = (d.company, d.parent_item_group, d.item_group, d.item_code)
		if key not in iwb_map:
			iwb_map[key] = frappe._dict({
				"opening_qty": 0.0, "opening_rate": 0.0, "opening_val": 0.0,
				"in_qty": 0.0, "in_rate": 0.0, "in_val": 0.0,
				"out_qty": 0.0, "out_rate": 0.0, "out_val": 0.0,
				"bal_qty": 0.0, "bal_rate": 0.0, "bal_val": 0.0,
				"val_rate": 0.0, "uom": None
			})

		qty_dict = iwb_map[(d.company, d.parent_item_group, d.item_group, d.item_code)]

		if d.voucher_type == "Stock Reconciliation":
			qty_diff = flt(d.qty_after_transaction) - qty_dict.bal_qty
                      
		else:
			qty_diff = flt(d.actual_qty)

		value_diff = flt(d.stock_value_difference)

		if d.posting_date < from_date:
			qty_dict.opening_qty += qty_diff
			qty_dict.opening_val += value_diff
                        
		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if qty_diff > 0:
				qty_dict.in_qty += qty_diff
				qty_dict.in_val += value_diff
			else:
				qty_dict.out_qty += abs(qty_diff)
				qty_dict.out_val += abs(value_diff)

		qty_dict.val_rate = d.valuation_rate
                qty_dict.opening_rate = 0
                qty_dict.in_rate = d.incoming_rate
                qty_dict.out_rate = d.outgoing_rate
		qty_dict.bal_qty += qty_diff
		qty_dict.bal_val += value_diff
                
	return iwb_map


def get_item_details(filters):
	condition = ''
	value = ()
	if filters.get("item_code"):
		condition = "where item_code=%s"
		value = (filters["item_code"],)

	items = frappe.db.sql("""select name, item_name, stock_uom, item_group, brand, description
		from tabItem {condition}""".format(condition=condition), value, as_dict=1)

	return dict((d.name, d) for d in items)

def validate_filters(filters):
	if not (filters.get("item_code") or filters.get("warehouse")):
		sle_count = flt(frappe.db.sql("""select count(name) from `tabStock Ledger Entry`""")[0][0])
		if sle_count > 500000:
			frappe.throw(_("Please set filter based on Item or Warehouse"))
