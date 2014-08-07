// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.accounts");

cur_frm.list_route = "Accounts Browser/Cost Center";

erpnext.accounts.CostCenterController = frappe.ui.form.Controller.extend({
	onload: function() {
		this.setup_queries();
	},

	setup_queries: function() {
		var me = this;
		if(this.frm.fields_dict["budget_details"].grid.get_field("account")) {
			this.frm.set_query("account", "budget_details", function() {
				return {
					filters:[
						['Account', 'company', '=', me.frm.doc.company],
						['Account', 'report_type', '=', 'Profit and Loss'],
						['Account', 'group_or_ledger', '=', 'Ledger'],
					]
				}
			});
		}

		this.frm.set_query("parent_cost_center", function() {
			return {
				filters:[
					['Cost Center', 'group_or_ledger', '=', 'Group'],
					['Cost Center', 'company', '=', me.frm.doc.company],
				]
			}
		});
	}
});

$.extend(cur_frm.cscript, new erpnext.accounts.CostCenterController({frm: cur_frm}));

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	var intro_txt = '';
	cur_frm.toggle_display('cost_center_name', doc.__islocal);
	cur_frm.toggle_enable(['group_or_ledger', 'company'], doc.__islocal);

	if(!doc.__islocal && doc.group_or_ledger=='Group') {
		intro_txt += __('Note: This Cost Center is a Group. Cannot make accounting entries against groups.');
	}

	cur_frm.cscript.hide_unhide_group_ledger(doc);

	cur_frm.toggle_display('sb1', doc.group_or_ledger=='Ledger')
	cur_frm.set_intro(intro_txt);

	cur_frm.appframe.add_button(__('Chart of Cost Centers'),
		function() { frappe.set_route("Accounts Browser", "Cost Center"); }, 'icon-sitemap')
}

cur_frm.cscript.parent_cost_center = function(doc, cdt, cdn) {
	if(!doc.company){
		msgprint(__('Please enter company name first'));
	}
}

cur_frm.cscript.hide_unhide_group_ledger = function(doc) {
	if (cstr(doc.group_or_ledger) == 'Group') {
		cur_frm.add_custom_button(__('Convert to Ledger'),
			function() { cur_frm.cscript.convert_to_ledger(); }, 'icon-retweet',
				"btn-default")
	} else if (cstr(doc.group_or_ledger) == 'Ledger') {
		cur_frm.add_custom_button(__('Convert to Group'),
			function() { cur_frm.cscript.convert_to_group(); }, 'icon-retweet',
				"btn-default")
	}
}

cur_frm.cscript.convert_to_ledger = function(doc, cdt, cdn) {
	return $c_obj(cur_frm.doc,'convert_group_to_ledger','',function(r,rt) {
		if(r.message == 1) {
			cur_frm.refresh();
		}
	});
}

cur_frm.cscript.convert_to_group = function(doc, cdt, cdn) {
	return $c_obj(cur_frm.doc,'convert_ledger_to_group','',function(r,rt) {
		if(r.message == 1) {
			cur_frm.refresh();
		}
	});
}
