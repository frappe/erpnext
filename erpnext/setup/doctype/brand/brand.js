// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on('Brand', {
	setup: (frm) => {
        frm.fields_dict["brand_defaults"].grid.get_field("default_warehouse").get_query = function(doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return {
				filters: { company: row.company }
			}
		}

        frm.fields_dict["brand_defaults"].grid.get_field("default_discount_account").get_query = function(doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return {
				filters: {
					'report_type': 'Profit and Loss',
					'company': row.company,
					"is_group": 0
				}
			};
		}

        frm.fields_dict["brand_defaults"].grid.get_field("buying_cost_center").get_query = function(doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return {
				filters: {
					"is_group": 0,
					"company": row.company
				}
			}
		}

        frm.fields_dict["brand_defaults"].grid.get_field("expense_account").get_query = function(doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return {
				query: "erpnext.controllers.queries.get_expense_account",
				filters: { company: row.company }
			}
		}

        frm.fields_dict["brand_defaults"].grid.get_field("default_provisional_account").get_query = function(doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return {
				filters: {
					"company": row.company,
					"root_type": ["in", ["Liability", "Asset"]],
					"is_group": 0
				}
			};
		}

        frm.fields_dict["brand_defaults"].grid.get_field("selling_cost_center").get_query = function(doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return {
				filters: {
					"is_group": 0,
					"company": row.company
				}
			}
		}

        frm.fields_dict["brand_defaults"].grid.get_field("income_account").get_query = function(doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return {
				query: "erpnext.controllers.queries.get_income_account",
				filters: { company: row.company }
			}
		}
	}
});