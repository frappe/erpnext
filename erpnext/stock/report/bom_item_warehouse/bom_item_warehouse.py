# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint
from frappe.utils import flt, getdate

def execute(filters=None):
        if not filters: filters = {}

        validate_filters(filters)

        columns = get_columns()
        item_map = get_item_details(filters)
        iwb_map = get_item_warehouse_map(filters)

        data = []
        summ_data = [] 
        bom_prev = "" 
        bom_work = "" 
        bom_count = 0 
        tot_bal_qty = 0 

        tot_bi_qty = 0
        
	for (company, bom, item, whse) in sorted(iwb_map):
                qty_dict = iwb_map[(company, bom, item, whse)]
                data.append([
                        bom, item, item_map[item]["description"],
                        item_map[item]["item_group"],
                        item_map[item]["item_name"], 
                        item_map[item]["stock_uom"], 
                        qty_dict.bal_qty, qty_dict.bi_qty, whse,                                              
                        item_map[item]["brand"], company
                    ])

       		
	for rows in data: 

		if bom_count == 0: 

       			bom_prev = rows[0] 

	                tot_bal_qty = tot_bal_qty + rows[6] 
			tot_bi_qty = tot_bi_qty + rows[7]
                        summ_data.append([bom_prev, rows[1], rows[2],
		 	rows[3], rows[4], rows[5], rows[7],
			rows[6], rows[8], rows[9], rows[10]
 			]) 
                else: 
			bom_work = rows[0] 

			if bom_prev == bom_work: 

				tot_bal_qty = tot_bal_qty + rows[6] 
				
				tot_bi_qty = tot_bi_qty + rows[7]
        	                summ_data.append([bom_prev, rows[1], rows[2],
			 	rows[3], rows[4], rows[5], rows[7],
				rows[6], rows[8], 
				rows[9], rows[10]				 
 				]) 
			else: 

				summ_data.append([bom_prev, " ", " ", 
			 	" ", " ", " ", tot_bi_qty,
				tot_bal_qty, " ", " ", " "
 				])				 

				summ_data.append([bom_work, rows[1], rows[2], 
			 	rows[3], rows[4], rows[5], rows[7], 
				rows[6], rows[8], 
				rows[9], rows[10] 
 				]) 
        	                        
				tot_bal_qty = 0 
 
 				tot_bi_qty = 0
        	                tot_bal_qty = tot_bal_qty + rows[6] 
				
				tot_bi_qty = tot_bi_qty + rows[7] 
				bom_prev = bom_work 
                               
		bom_count = bom_count + 1 
	summ_data.append([bom_prev, " ", " ", 
		" ", " ", " ", tot_bi_qty,
		tot_bal_qty, " ", " ", " "
 		])	 

						 
	return columns, summ_data 



def get_columns():
        """return columns"""
        columns = [
		_("BOM")+":Link/BOM:100",
                _("Item")+":Link/Item:100",
                _("Description")+"::140",
                _("Item Group")+"::100",
                _("Item Name")+"::150",
 #               _("Warehouse")+":Link/Warehouse:100",
                _("Stock UOM")+":Link/UOM:90",
		_("BoM Qty")+":Float:100",
                _("Balance Qty")+":Float:100",
                _("Warehouse")+"::100",
                _("Brand")+":Link/Company:100",
		_("Company")+"::100",
              
         ]

        return columns

def get_conditions(filters):
        conditions = ""
	
	if filters.get("company"):
                conditions += " and bo.company = '%s'" % frappe.db.escape(filters.get("company"), percent=False)

        if filters.get("item_code"):
                conditions += " and item_code = '%s'" % frappe.db.escape(filters.get("item_code"), percent=False)
     
        if filters.get("bom"):
                conditions += " and bi.parent = '%s'" % frappe.db.escape(filters.get("bom"), percent=False)

#       if filters.get("warehouse"):
  #             conditions += " and warehouse = '%s'" % frappe.db.escape(filters.get("warehouse"), percent=False)
        return conditions


def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)

	if filters.get("include_exploded_items") == "Y":
	        
        	return frappe.db.sql("""select bo.name, bo.company, bi.item_code, bi.qty as bi_qty
                	from `tabBOM` bo, `tabBOM Explosion Item` bi where bo.name = bi.parent %s
                	order by bo.company, bo.name, bi.item_code""" % conditions, as_dict=1)
	else:

        	return frappe.db.sql("""select bo.name, bo.company, bi.item_code, bi.qty as bi_qty
                	from `tabBOM` bo, `tabBOM Item` bi where bo.name = bi.parent %s
       	        	order by bo.company, bo.name, bi.item_code""" % conditions, as_dict=1)

def get_item_warehouse_map(filters):
        iwb_map = {}
        from_date = getdate(filters["from_date"])
        to_date = getdate(filters["to_date"])

        sle = get_stock_ledger_entries(filters)
	company = filters.get("company")
	total_stock = 0
	if filters.get("warehouse"):
		whse = filters.get("warehouse")
	else:
		whse = get_warehouses(company)
	
	
        for d in sle:
		if filters.get("warehouse"):
			key = (d.company, d.name, d.item_code, whse)
				
                	if key not in iwb_map:
                        	iwb_map[key] = frappe._dict({
                                	"opening_qty": 0.0, "opening_val": 0.0,
                                	"in_qty": 0.0, "in_val": 0.0,
                                	"out_qty": 0.0, "out_val": 0.0,
                                	"bal_qty": 0.0, 
                                	"bi_qty": 0.0,
                                	"val_rate": 0.0, "uom": None
                        	})

	                qty_dict = iwb_map[(d.company, d.name, d.item_code, whse)]
		
			qty_dict.bal_qty = get_stock(d.item_code, d.company, whse)
		
        	        qty_dict.bi_qty = d.bi_qty

		else:

			total_stock = get_total_stock(d.item_code, d.company)
			if total_stock > 0:

				for w in whse:

					whse_stock = get_stock(d.item_code, d.company, w)

					if whse_stock > 0:
			                	key = (d.company, d.name, d.item_code, w)
					
        		        		if key not in iwb_map:
        		                		iwb_map[key] = frappe._dict({
        		                        		"opening_qty": 0.0, "opening_val": 0.0,
        		                        		"in_qty": 0.0, "in_val": 0.0,
        		                        		"out_qty": 0.0, "out_val": 0.0,
        		                        		"bal_qty": 0.0, 
        		                        		"bi_qty": 0.0,
        		                        		"val_rate": 0.0, "uom": None
        		                		})

			                	qty_dict = iwb_map[(d.company, d.name, d.item_code, w)]
			
						qty_dict.bal_qty = whse_stock
		
        			        	qty_dict.bi_qty = d.bi_qty
	
			
			else:

				key = (d.company, d.name, d.item_code, " ")
					
        	        	if key not in iwb_map:
        	                	iwb_map[key] = frappe._dict({
        	                        	"opening_qty": 0.0, "opening_val": 0.0,
        	                        	"in_qty": 0.0, "in_val": 0.0,
        	                        	"out_qty": 0.0, "out_val": 0.0,
        	                        	"bal_qty": 0.0, 
        	                        	"bi_qty": 0.0,
        	                        	"val_rate": 0.0, "uom": None
        	                	})

		                qty_dict = iwb_map[(d.company, d.name, d.item_code, " ")]
		
				qty_dict.bal_qty = 0
		
        		        qty_dict.bi_qty = d.bi_qty
				
				
	return iwb_map

	      
def get_warehouses(company):
		whse = frappe.db.sql("""select name from `tabWarehouse` where company = %s""", company)
		return whse

def get_stock(item_code, company, warehouse):
		
                item_whse_stock = flt(frappe.db.sql("""select sum(actual_qty)
			from `tabStock Ledger Entry`
			where item_code=%s and company = %s and warehouse = %s""",
			(item_code, company, warehouse))[0][0])
		stock_whse_recon = flt(frappe.db.sql("""select sum(qty_after_transaction)
			from `tabStock Ledger Entry`
			where item_code=%s and company = %s and warehouse = %s and voucher_type = 'Stock Reconciliation'""",
			(item_code, company, warehouse))[0][0])

		tot_whse_stock = item_whse_stock + stock_whse_recon
		
       	        return tot_whse_stock

def get_total_stock(item_code, company):
		
                item_stock = flt(frappe.db.sql("""select sum(actual_qty)
			from `tabStock Ledger Entry`
			where item_code=%s and company = %s""",
			(item_code, company))[0][0])
		
		stock_recon = flt(frappe.db.sql("""select sum(qty_after_transaction)
			from `tabStock Ledger Entry`
			where item_code=%s and company = %s and voucher_type = 'Stock Reconciliation'""",
			(item_code, company))[0][0])

		tot_stock = item_stock + stock_recon
		return tot_stock

def get_stock_val(item_code, company, warehouse):
		
                item_stock_val = flt(frappe.db.sql("""select sum(stock_value)
			from `tabStock Ledger Entry`
			where item_code=%s and company = %s and warehouse = %s""",
			(item_code, company, warehouse))[0][0])

		stock_recon_val = flt(frappe.db.sql("""select sum(stock_value_difference)
			from `tabStock Ledger Entry`
			where item_code=%s and company = %s and voucher_type = 'Stock Reconciliation'""",
			(item_code, company))[0][0])

		tot_stock_val = item_stock_val + stock_recon_val
		
       	        return tot_stock_val

def get_item_details(filters):
        condition = ''
        value = ()
        if filters.get("item_code"):
                condition = "where item_code=%s"
                value = (filters["item_code"],)

        items = frappe.db.sql("""select item_group, item_name, stock_uom, name, brand, description
                from tabItem {condition}""".format(condition=condition), value, as_dict=1)
		
        return dict((d.name, d) for d in items)

def validate_filters(filters):
        if not (filters.get("item_code") or filters.get("warehouse")):
                sle_count = flt(frappe.db.sql("""select count(name) from `tabStock Ledger Entry`""")[0][0])
                if sle_count > 500000:
                        frappe.throw(_("Please set filter based on Item or Warehouse"))



