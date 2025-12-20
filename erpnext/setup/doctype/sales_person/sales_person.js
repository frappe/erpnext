// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Sales Person", {
	refresh: function (frm) {
		if (frm.doc.__onload && frm.doc.__onload.dashboard_info) {
			let info = frm.doc.__onload.dashboard_info;
			frm.dashboard.add_indicator(
				__("Total Contribution Amount Against Orders: {0}", [
					format_currency(info.allocated_amount_against_order, info.currency),
				]),
				"blue"
			);

			frm.dashboard.add_indicator(
				__("Total Contribution Amount Against Invoices: {0}", [
					format_currency(info.allocated_amount_against_invoice, info.currency),
				]),
				"blue"
			);
		}
		frm.trigger("set_root_readonly");
	},

	setup: function (frm) {
		frm.fields_dict["targets"].grid.get_field("distribution_id").get_query = function (doc, cdt, cdn) {
			var row = locals[cdt][cdn];
			return {
				filters: {
					fiscal_year: row.fiscal_year,
				},
			};
		};

		frm.make_methods = {
			"Sales Order": () =>
				frappe
					.new_doc("Sales Order")
					.then(() => frm.add_child("sales_team", { sales_person: frm.doc.name })),
		};
	},
	set_root_readonly: function (frm) {
		// read-only for root
		if (!frm.doc.parent_sales_person && !frm.doc.__islocal) {
			frm.set_read_only();
			frm.set_intro(__("This is a root sales person and cannot be edited."));
		} else {
			frm.set_intro(null);
		}
	},
});

//get query select sales person
cur_frm.fields_dict["parent_sales_person"].get_query = function (doc, cdt, cdn) {
	return {
		filters: [
			["Sales Person", "is_group", "=", 1],
			["Sales Person", "name", "!=", doc.sales_person_name],
		],
	};
};

cur_frm.fields_dict.employee.get_query = function (doc, cdt, cdn) {
	return { query: "erpnext.controllers.queries.employee_query" };
};
