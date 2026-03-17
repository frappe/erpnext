// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Global Defaults", {
	refresh: function (frm) {
		if (!frm.doc.demo_company) {
			frm.add_custom_button(
				__("Setup Demo Data"),
				function () {
					frappe.confirm(
						__("This will create a Demo Company and generate sample transactions. Continue?"),
						function () {
							frappe.call({
								method: "erpnext.setup.demo.setup_demo_data",
								freeze: true,
								freeze_message: __("Create Demo Data..."),
								callback: function (r) {
									if (!r.exc) {
										frm.reload_doc();
									}
								},
								error: function () {
									frappe.msgprint({
										title: __("Error"),
										message: __("Failed to create demo data. Check the error log."),
										indicator: "red",
									});
								},
							});
						}
					);
				},
				__("Demo")
			);
		}

		frm.add_custom_button(
			__("Clear Demo Data"),
			function () {
				frappe.confirm(
					__("Are you sure you want to clear all demo data? This cannot be undone."),
					function () {
						frappe.call({
							method: "erpnext.setup.demo.clear_demo_data",
							freeze: true,
							freeze_message: __("Clearing Demo Data..."),
							callback: function (r) {
								if (!r.exc) {
									frappe.msgprint({
										title: __("Success"),
										message: __("Demo data has been cleared successfully."),
										indicator: "green",
									});
									frm.reload_doc();
								}
							},
							error: function () {
								frappe.msgprint({
									title: __("Error"),
									message: __("Failed to clear demo data. Check the error log."),
									indicator: "red",
								});
							},
						});
					}
				);
			},
			__("Demo")
		);
	},
	onload: function (frm) {
		frm.trigger("get_distance_uoms");
	},
	validate: function (frm) {
		frm.call("get_defaults", null, (r) => {
			frappe.sys_defaults = r.message;
		});
	},
	get_distance_uoms: function (frm) {
		let units = [];

		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "UOM Conversion Factor",
				filters: { category: __("Length") },
				fields: ["to_uom"],
				limit_page_length: 500,
			},
			callback: function (r) {
				r.message.forEach((row) => units.push(row.to_uom));
			},
		});
		frm.set_query("default_distance_unit", function () {
			return { filters: { name: ["IN", units] } };
		});
	},
});
