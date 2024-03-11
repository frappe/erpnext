// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Supplier Group", {
	setup: function (frm) {
		frm.set_query("parent_supplier_group", function (doc) {
			return {
				filters: {
					is_group: 1,
					name: ["!=", cur_frm.doc.supplier_group_name],
				},
			};
		});

		frm.set_query("account", "accounts", function (doc, cdt, cdn) {
			return {
				filters: {
					root_type: "Liability",
					account_type: "Payable",
					company: locals[cdt][cdn].company,
					is_group: 0,
				},
			};
		});

		frm.set_query("advance_account", "accounts", function (doc, cdt, cdn) {
			return {
				filters: {
					root_type: "Asset",
					account_type: "Payable",
					company: locals[cdt][cdn].company,
					is_group: 0,
				},
			};
		});
	},
	refresh: function (frm) {
		frm.set_intro(frm.doc.__islocal ? "" : __("There is nothing to edit."));
		frm.trigger("set_root_readonly");
	},
	set_root_readonly: function (frm) {
		if (!frm.doc.parent_supplier_group && !frm.doc.__islocal) {
			frm.trigger("set_read_only");
			frm.set_intro(__("This is a root supplier group and cannot be edited."));
		} else {
			frm.set_intro(null);
		}
	},
});
