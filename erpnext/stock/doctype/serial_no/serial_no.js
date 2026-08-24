// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Serial No", {
	setup(frm) {
		frm.add_fetch("customer", "customer_name", "customer_name");
		frm.add_fetch("supplier", "supplier_name", "supplier_name");
		frm.add_fetch("item_code", "item_name", "item_name");
		frm.add_fetch("item_code", "description", "description");
		frm.add_fetch("item_code", "item_group", "item_group");
		frm.add_fetch("item_code", "brand", "brand");

		frm.set_query("item_code", function () {
			return erpnext.queries.item({ is_stock_item: 1, has_serial_no: 1 });
		});

		frm.set_query("work_order", () => {
			return {
				filters: {
					docstatus: 1,
				},
			};
		});
	},

	refresh(frm) {
		frm.toggle_enable("item_code", frm.doc.__islocal);
		frm.trigger("view_ledgers");
	},

	view_ledgers(frm) {
		frm.add_custom_button(__("View Ledgers"), () => {
			frappe.route_options = {
				item_code: frm.doc.item_code,
				serial_no: frm.doc.name,
				posting_date: frappe.datetime.now_date(),
				posting_time: frappe.datetime.now_time(),
			};
			frappe.set_route("query-report", "Serial No Ledger");
		});
	},
});
