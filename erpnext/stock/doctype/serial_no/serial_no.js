// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch("customer", "customer_name", "customer_name")
cur_frm.add_fetch("supplier", "supplier_name", "supplier_name")

cur_frm.add_fetch("item_code", "item_name", "item_name")
cur_frm.add_fetch("item_code", "description", "description")
cur_frm.add_fetch("item_code", "item_group", "item_group")
cur_frm.add_fetch("item_code", "brand", "brand")

cur_frm.cscript.onload = function() {
	cur_frm.set_query("item_code", function() {
		return erpnext.queries.item({"is_stock_item": "Yes", "has_serial_no": "Yes"})
	});
};

frappe.ui.form.on("Serial No", "refresh", function(frm) {
	frm.toggle_enable("item_code", frm.doc.__islocal);

	if(frm.doc.status == "Sales Returned" && frm.doc.warehouse)
		cur_frm.add_custom_button(__('Set Status as Available'), function() {
			cur_frm.set_value("status", "Available");
			cur_frm.save();
		}, "icon-ok", "btn-default");
});
