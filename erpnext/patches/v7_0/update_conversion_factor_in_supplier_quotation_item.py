from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('buying', 'doctype', 'supplier_quotation_item')

	frappe.db.sql("""update 
			`tabSupplier Quotation Item` as sqi_t,
			(select sqi.item_code as item_code, sqi.uom as uom, ucd.conversion_factor as conversion_factor  
				from `tabSupplier Quotation Item` sqi left join `tabUOM Conversion Detail` ucd  
				on ucd.uom = sqi.uom and sqi.item_code = ucd.parent) as conversion_data,
			`tabItem` as item
		set 
			sqi_t.conversion_factor= ifnull(conversion_data.conversion_factor, 1), 
			sqi_t.stock_qty = (ifnull(conversion_data.conversion_factor, 1) * sqi_t.qty), 
			sqi_t.stock_uom = item.stock_uom  
		where 
			sqi_t.item_code = conversion_data.item_code and
			sqi_t.uom = conversion_data.uom and sqi_t.item_code = item.name""")