SELECT 
	dn.name, dn.posting_date, dn.posting_time, dn_item.item_code,
	dn_item.item_name, dn_item.description, dn_item.warehouse, 
	dn.project_name, dn_item.qty, dn_item.basic_rate, dn_item.amount, dn_item.name
FROM 
	`tabDelivery Note Item` dn_item, `tabDelivery Note` dn 
WHERE 
 	dn_item.parent = dn.name
	AND dn.docstatus = 1
	AND dn.name like '%(name)s%%'
	AND ifnull(dn_item.item_code, '') like '%(item_code)s%%'
	AND ifnull(dn.project_name, '') like '%(project_name)s%%'
	AND dn.posting_date >= '%(posting_date)s'
	AND dn.posting_date <= '%(posting_date1)s'
ORDER BY dn.name DESC