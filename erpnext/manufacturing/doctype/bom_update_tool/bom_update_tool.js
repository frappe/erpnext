// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('BOM Update Tool', {
	setup: function(frm) {
		frm.set_query("current_bom", function() {
			return {
				query: "erpnext.controllers.queries.bom",
				filters: {name: "!" + frm.doc.new_bom}
			};
		});

		frm.set_query("new_bom", function() {
			return {
				query: "erpnext.controllers.queries.bom",
				filters: {name: "!" + frm.doc.current_bom}
			};
		});
	},

	refresh: function(frm) {
		frm.disable_save();
		frm.events.disable_button(frm, "replace");

		frm.add_custom_button(__("View BOM Update Log"), () => {
			frappe.set_route("List", "BOM Update Log");
		});
	},

	disable_button: (frm, field, disable=true) => {
		frm.get_field(field).input.disabled = disable;
	},

	new_bom: (frm) => {
		if (frm.doc.new_bom) {
			frm.events.disable_button(frm, "replace", false);
		} else {
			frm.events.disable_button(frm, "replace", true);
		}
	},

	replace: (frm) => {
		if (frm.doc.new_bom) {
			if (frm.doc.current_bom) {
				frm.events.replace_action(frm);
			} else {
				frappe.call({
					method: "erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool.get_old_bom_references",
					freeze: true,
					args: {
						new_bom_name: frm.doc.new_bom
					},
					callback: result => {
						if (result.message && result.message.length) {
							let ls = `<p>Update the following BOM Item references?</p>
							<table class='form-grid' style='overflow-wrap: anywhere'>
							<thead class='grid-heading-row'><tr><th class='form-grid'>BOM Name</th></tr></thead><tbody>`;
							for (const bom_name of result.message) {
								ls = ls + `<tr><td class='form-grid'><a href="/app/bom/${bom_name}" target="_blank">${bom_name}</a></td></tr>`;
							}
							ls = ls + "</tbody></table>";
							const dialog = frappe.confirm(ls, ()=>frm.events.replace_action(frm));
						} else {
							frappe.show_alert({message: __("Nothing to do!"), indicator: "green"}, 5);
						}
					}
				});
			}
		}
	},

	replace_action: (frm) => {
		if (frm.doc.new_bom) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool.enqueue_replace_bom",
				freeze: true,
				args: {
					boms: {
						"current_bom": frm.doc.current_bom || null,
						"new_bom": frm.doc.new_bom
					}
				},
				callback: result => {
					if (result && result.message && !result.exc) {
						frm.events.confirm_job_start(frm, result.message);
					}
				}
			});
		}
	},

	update_latest_price_in_all_boms: (frm) => {
		frappe.call({
			method: "erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool.enqueue_update_cost",
			freeze: true,
			callback: result => {
				if (result && result.message && !result.exc) {
					frm.events.confirm_job_start(frm, result.message);
				}
			}
		});
	},

	confirm_job_start: (frm, log_data) => {
		let log_link = frappe.utils.get_form_link("BOM Update Log", log_data.name, true);
		frappe.msgprint({
			"message": __("BOM Updation is queued and may take a few minutes. Check {0} for progress.", [log_link]),
			"title": __("BOM Update Initiated"),
			"indicator": "blue"
		});
	}
});
