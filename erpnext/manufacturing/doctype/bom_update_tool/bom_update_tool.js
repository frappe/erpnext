// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("BOM Update Tool", {
	setup: function (frm) {
		frm.set_query("current_bom", function () {
			return {
				query: "erpnext.controllers.queries.bom",
				filters: { name: "!" + frm.doc.new_bom },
			};
		});

		frm.set_query("new_bom", function () {
			return {
				query: "erpnext.controllers.queries.bom",
				filters: { name: "!" + frm.doc.current_bom },
			};
		});
	},

	refresh: function (frm) {
		frm.disable_save();
		frm.events.disable_button(frm, "replace");

		frm.add_custom_button(__("View BOM Update Log"), () => {
			frappe.set_route("List", "BOM Update Log");
		});
	},

	disable_button: (frm, field, disable = true) => {
		frm.get_field(field).input.disabled = disable;
	},

	current_bom: (frm) => {
		if (frm.doc.current_bom && frm.doc.new_bom) {
			frm.events.disable_button(frm, "replace", false);
		}
	},

	new_bom: (frm) => {
		if (frm.doc.current_bom && frm.doc.new_bom) {
			frm.events.disable_button(frm, "replace", false);
		}
	},

	replace: (frm) => {
		if (frm.doc.current_bom && frm.doc.new_bom) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool.enqueue_replace_bom",
				freeze: true,
				args: {
					boms: {
						current_bom: frm.doc.current_bom,
						new_bom: frm.doc.new_bom,
					},
				},
				callback: (result) => {
					if (result && result.message && !result.exc) {
						frm.events.confirm_job_start(frm, result.message);
					}
				},
			});
		}
	},

	update_latest_price_in_all_boms: (frm) => {
		frappe.call({
			method: "erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool.enqueue_update_cost",
			freeze: true,
			callback: (result) => {
				if (result && result.message && !result.exc) {
					frm.events.confirm_job_start(frm, result.message);
				}
			},
		});
	},

	confirm_job_start: (frm, log_data) => {
		let log_link = frappe.utils.get_form_link("BOM Update Log", log_data.name, true);
		frappe.msgprint({
			message: __("BOM Updation is queued and may take a few minutes. Check {0} for progress.", [
				log_link,
			]),
			title: __("BOM Update Initiated"),
			indicator: "blue",
		});
	},
});
