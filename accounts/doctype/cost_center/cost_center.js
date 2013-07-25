// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

wn.provide("erpnext.accounts");
erpnext.accounts.CostCenterController = wn.ui.form.Controller.extend({
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
						['Account', 'is_pl_account', '=', 'Yes'],
						['Account', 'debit_or_credit', '=', 'Debit'],
						['Account', 'group_or_ledger', '!=', 'Group'],
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
		intro_txt += '<p><b>Note:</b> This Cost Center is a <i>Group</i>, \
			Accounting Entries are not allowed against groups.</p>';
	}

	cur_frm.cscript.hide_unhide_group_ledger(doc);
	
	cur_frm.toggle_display('sb1', doc.group_or_ledger=='Ledger')
	cur_frm.set_intro(intro_txt);
	
	cur_frm.add_custom_button('Chart of Cost Centers', 
		function() { wn.set_route("Accounts Browser", "Cost Center"); }, 'icon-sitemap')
}

cur_frm.cscript.parent_cost_center = function(doc,cdt,cdn){
	if(!doc.company){
		alert('Please enter company name first');
	}
}

cur_frm.cscript.hide_unhide_group_ledger = function(doc) {
	if (cstr(doc.group_or_ledger) == 'Group') {
		cur_frm.add_custom_button('Convert to Ledger', 
			function() { cur_frm.cscript.convert_to_ledger(); }, 'icon-retweet')
	} else if (cstr(doc.group_or_ledger) == 'Ledger') {
		cur_frm.add_custom_button('Convert to Group', 
			function() { cur_frm.cscript.convert_to_group(); }, 'icon-retweet')
	}
}

cur_frm.cscript.convert_to_ledger = function(doc, cdt, cdn) {
	$c_obj(cur_frm.get_doclist(),'convert_group_to_ledger','',function(r,rt) {
		if(r.message == 1) {
			cur_frm.refresh();
		}
	});
}

cur_frm.cscript.convert_to_group = function(doc, cdt, cdn) {
	$c_obj(cur_frm.get_doclist(),'convert_ledger_to_group','',function(r,rt) {
		if(r.message == 1) {
			cur_frm.refresh();
		}
	});
}
