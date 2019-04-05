// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	onload: function (doc, cdt, cdn) {
		cur_frm.trigger("get_distance_uoms");
	},

	validate: function (doc, cdt, cdn) {
		return $c_obj(doc, 'get_defaults', '', function (r, rt) {
			frappe.sys_defaults = r.message;
		});
	},

	get_distance_uoms: function (frm) {
		let units = [];

		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "UOM Conversion Factor",
				filters: { "category": "Length" },
				fields: ["to_uom"],
				limit_page_length: 500
			},
			callback: function (r) {
				r.message.forEach(row => units.push(row.to_uom));
			}
		});

		cur_frm.set_query("default_distance_unit", function (doc) {
			return { filters: { "name": ["IN", units] } };
		})
	}
});
