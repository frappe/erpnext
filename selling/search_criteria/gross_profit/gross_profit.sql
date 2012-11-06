SELECT 
	dn.name, dn.posting_date, dn.posting_time, dn_item.item_code,
	dn_item.item_name, dn_item.description, dn_item.warehouse, 
	dn.project_name, dn_item.qty, dn_item.basic_rate, dn_item.amount, dn_item.name
FROM 
	`tabDelivery Note Item` dn_item, `tabDelivery Note` dn 
WHERE 
	dn.docstatus = 1
 	AND dn_item.parent = dn.name
ORDER BY dn.name DESC