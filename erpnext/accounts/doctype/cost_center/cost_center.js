// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.accounts");

frappe.ui.form.on("Cost Center", {
	onload: function (frm) {
		frm.set_query("parent_cost_center", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 1,
				},
			};
		});
	},
	refresh: function (frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Update Cost Center Name / Number"), function () {
				frm.trigger("update_cost_center_number");
			});
		}

		let intro_txt = "";
		let doc = frm.doc;
		frm.toggle_display("cost_center_name", doc.__islocal);
		frm.toggle_enable(["is_group", "company"], doc.__islocal);

		if (!doc.__islocal && doc.is_group == 1) {
			intro_txt += __(
				"Note: This Cost Center is a Group. Cannot make accounting entries against groups."
			);
		}

		frm.events.hide_unhide_group_ledger(frm);

		frm.toggle_display("sb1", doc.is_group == 0);
		frm.set_intro(intro_txt);

		if (!frm.doc.__islocal) {
			frm.add_custom_button(__("Chart of Cost Centers"), function () {
				frappe.set_route("Tree", "Cost Center");
			});

			frm.add_custom_button(__("Budget"), function () {
				frappe.set_route("List", "Budget", { cost_center: frm.doc.name });
			});
		}
	},
	update_cost_center_number: function (frm) {
		var d = new frappe.ui.Dialog({
			title: __("Update Cost Center Name / Number"),
			fields: [
				{
					label: "Cost Center Name",
					fieldname: "cost_center_name",
					fieldtype: "Data",
					reqd: 1,
					default: frm.doc.cost_center_name,
				},
				{
					label: "Cost Center Number",
					fieldname: "cost_center_number",
					fieldtype: "Data",
					default: frm.doc.cost_center_number,
				},
				{
					label: __("Merge with existing"),
					fieldname: "merge",
					fieldtype: "Check",
					default: 0,
				},
			],
			primary_action: function () {
				let data = d.get_values();
				if (
					data.cost_center_name === frm.doc.cost_center_name &&
					data.cost_center_number === frm.doc.cost_center_number
				) {
					d.hide();
					return;
				}
				frappe.dom.freeze();
				frappe.call({
					method: "erpnext.accounts.utils.update_cost_center",
					args: {
						docname: frm.doc.name,
						cost_center_name: data.cost_center_name,
						cost_center_number: cstr(data.cost_center_number),
						company: frm.doc.company,
						merge: data.merge,
					},
					callback: function (r) {
						frappe.dom.unfreeze();
						if (!r.exc) {
							if (r.message) {
								frappe.set_route("Form", "Cost Center", r.message);
							} else {
								frm.set_value("cost_center_name", data.cost_center_name);
								frm.set_value("cost_center_number", data.cost_center_number);
							}
							d.hide();
						}
					},
				});
			},
			primary_action_label: __("Update"),
		});
		d.show();
	},

	parent_cost_center(frm) {
		if (!frm.doc.company) {
			frappe.msgprint(__("Please enter company name first"));
		}
	},

	hide_unhide_group_ledger(frm) {
		let doc = frm.doc;
		if (doc.is_group == 1) {
			frm.add_custom_button(__("Convert to Non-Group"), () => frm.events.convert_to_ledger(frm));
		} else if (doc.is_group == 0) {
			frm.add_custom_button(__("Convert to Group"), () => frm.events.convert_to_group(frm));
		}
	},

	convert_to_group(frm) {
		frm.call("convert_ledger_to_group").then((r) => {
			if (r.message === 1) {
				frm.refresh();
			}
		});
	},

	convert_to_ledger(frm) {
		frm.call("convert_group_to_ledger").then((r) => {
			if (r.message === 1) {
				frm.refresh();
			}
		});
	},
});
