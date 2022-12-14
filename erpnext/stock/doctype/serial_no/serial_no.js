// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch("customer", "customer_name", "customer_name")
cur_frm.add_fetch("supplier", "supplier_name", "supplier_name")

cur_frm.add_fetch("item_code", "item_name", "item_name")
cur_frm.add_fetch("item_code", "description", "description")
cur_frm.add_fetch("item_code", "item_group", "item_group")
cur_frm.add_fetch("item_code", "brand", "brand")

cur_frm.cscript.onload = function() {
	cur_frm.set_query("item_code", function() {
		return erpnext.queries.item({"is_stock_item": 1, "has_serial_no": 1})
	});

	cur_frm.set_query("sales_order", function() {
		return {
			filters: {'docstatus': ['!=', 2]}
		};
	});
};

frappe.ui.form.on("Serial No", "refresh", function(frm) {
	if(!frm.is_new()) {
		frm.add_custom_button(__("View Ledger"), () => {
			frappe.route_options = {
				serial_no: frm.doc.name,
				from_date: frappe.defaults.get_user_default("year_start_date"),
				to_date: frappe.defaults.get_user_default("year_end_date")
			};
			frappe.set_route("query-report", "Stock Ledger");
		});
	}

	frm.toggle_enable("item_code", frm.doc.__islocal);

	if (frm.fields_dict.maintenance_schedule_html && !frm.doc.__islocal) {
		var wrapper = frm.fields_dict.maintenance_schedule_html.wrapper;
		$(wrapper).html(frappe.render_template("maintenance_schedule", { data: frm.doc}));
	}
});
