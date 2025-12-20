// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Territory", {
	setup: function (frm) {
		frm.fields_dict["targets"].grid.get_field("distribution_id").get_query = function (doc, cdt, cdn) {
			var row = locals[cdt][cdn];
			return {
				filters: {
					fiscal_year: row.fiscal_year,
				},
			};
		};
	},
	refresh: function (frm) {
		frm.trigger("set_root_readonly");
	},
	set_root_readonly: function (frm) {
		// read-only for root territory
		if (!frm.doc.parent_territory && !frm.doc.__islocal) {
			frm.set_read_only();
			frm.set_intro(__("This is a root territory and cannot be edited."));
		} else {
			frm.set_intro(null);
		}
	},
});

//get query select territory
cur_frm.fields_dict["parent_territory"].get_query = function (doc, cdt, cdn) {
	return {
		filters: [
			["Territory", "is_group", "=", 1],
			["Territory", "name", "!=", doc.territory_name],
		],
	};
};
