// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stock Settings", {
	refresh: function (frm) {
		let filters = function () {
			return {
				filters: {
					is_group: 0,
				},
			};
		};

		frm.set_query("default_warehouse", filters);
		frm.set_query("sample_retention_warehouse", filters);
	},

	use_serial_batch_fields(frm) {
		if (frm.doc.use_serial_batch_fields && !frm.doc.disable_serial_no_and_batch_selector) {
			frm.set_value("disable_serial_no_and_batch_selector", 1);
		}
	},

	disable_serial_no_and_batch_selector(frm) {
		if (!frm.doc.disable_serial_no_and_batch_selector && frm.doc.use_serial_batch_fields) {
			frm.set_value("disable_serial_no_and_batch_selector", 1);
			frappe.msgprint(
				__("Serial No and Batch Selector cannot be use when Use Serial / Batch Fields is enabled.")
			);
		}
	},

	allow_negative_stock: function (frm) {
		if (!frm.doc.allow_negative_stock) {
			return;
		}

		let msg = __(
			"Using negative stock disables FIFO/Moving average valuation when inventory is negative."
		);
		msg += " ";
		msg += __("This is considered dangerous from accounting point of view.");
		msg += "<br>";
		msg += __("Do you still want to enable negative inventory?");

		frappe.confirm(
			msg,
			() => {},
			() => {
				frm.set_value("allow_negative_stock", 0);
			}
		);
	},
});
