frappe.listview_settings['Sales Order'] = {
	add_fields: ["`tabSales Order`.`grand_total`", "`tabSales Order`.`company`", "`tabSales Order`.`currency`",
		"`tabSales Order`.`customer`", "`tabSales Order`.`customer_name`", "`tabSales Order`.`per_delivered`",
		"`tabSales Order`.`per_billed`", "`tabSales Order`.`delivery_date`"],
	filters: [["per_delivered", "<", 100]]
};
