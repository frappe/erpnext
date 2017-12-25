// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include "erpnext/public/js/controllers/accounts.js" %}

frappe.ui.form.on("POS Profile", "onload", function(frm) {
	frm.set_query("selling_price_list", function() {
		return { filters: { selling: 1 } };
	});

	erpnext.queries.setup_queries(frm, "Warehouse", function() {
		return erpnext.queries.warehouse(frm.doc);
	});

	frm.call({
		method: "erpnext.accounts.doctype.pos_profile.pos_profile.get_series",
		callback: function(r) {
			if(!r.exc) {
				set_field_options("naming_series", r.message);
			}
		}
	});
});

frappe.ui.form.on('POS Profile', {
	setup: function(frm) {
		frm.set_query("print_format_for_online", function() {
			return {
				filters: [
					['Print Format', 'doc_type', '=', 'Sales Invoice'],
					['Print Format', 'print_format_type', '=', 'Server'],
				]
			};
		});

		frm.set_query("print_format", function() {
			return { filters: { doc_type: "Sales Invoice", print_format_type: "Js"} };
		});

		frappe.db.get_value('POS Settings', {name: 'POS Settings'}, 'use_pos_in_offline_mode', (r) => {
			is_offline = r && cint(r.use_pos_in_offline_mode)
			frm.toggle_display('offline_pos_section', is_offline);
			frm.toggle_display('print_format_for_online', !is_offline);
		});
	},

	refresh: function(frm) {
		if(frm.doc.company) {
			frm.trigger("toggle_display_account_head");
		}
	},
	
	company: function(frm) {
		frm.trigger("toggle_display_account_head");
	},
	
	toggle_display_account_head: function(frm) {
		frm.toggle_display('expense_account',
			erpnext.is_perpetual_inventory_enabled(frm.doc.company));
	}
})

// Income Account
// --------------------------------
cur_frm.fields_dict['income_account'].get_query = function(doc,cdt,cdn) {
	return{
		filters:{
			'is_group': 0,
			'company': doc.company,
			'account_type': "Income Account"
		}
	};
};


// Cost Center
// -----------------------------
cur_frm.fields_dict['cost_center'].get_query = function(doc,cdt,cdn) {
	return{
		filters:{
			'company': doc.company,
			'is_group': 0
		}
	};
};


// Expense Account
// -----------------------------
cur_frm.fields_dict["expense_account"].get_query = function(doc) {
	return {
		filters: {
			"report_type": "Profit and Loss",
			"company": doc.company,
			"is_group": 0
		}
	};
};

// ------------------ Get Print Heading ------------------------------------
cur_frm.fields_dict['select_print_heading'].get_query = function(doc, cdt, cdn) {
	return{
		filters:[
			['Print Heading', 'docstatus', '!=', 2]
		]
	};
};

cur_frm.fields_dict.write_off_account.get_query = function(doc) {
	return{
		filters:{
			'report_type': 'Profit and Loss',
			'is_group': 0,
			'company': doc.company
		}
	};
};

// Write off cost center
// -----------------------
cur_frm.fields_dict.write_off_cost_center.get_query = function(doc) {
	return{
		filters:{
			'is_group': 0,
			'company': doc.company
		}
	};
};
