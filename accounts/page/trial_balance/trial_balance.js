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
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.	If not, see <http://www.gnu.org/licenses/>.

wn.require("app/js/account_tree_grid.js");

wn.pages['trial-balance'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: 'Trial Balance',
		single_column: true
	});
	var TrialBalance = erpnext.AccountTreeGrid.extend({
		export: function() {
			var msgbox = msgprint('<p>Select To Download:</p>\
				<p><input type="checkbox" name="with_groups" checked> Account Groups</p>\
				<p><input type="checkbox" name="with_ledgers" checked> Account Ledgers</p>\
				<p><button class="btn btn-info btn-small">Download</button>');

			var me = this;

			$(msgbox.body).find("button").click(function() {
				var with_groups = $(msgbox.body).find("[name='with_groups']").is(":checked");
				var with_ledgers = $(msgbox.body).find("[name='with_ledgers']").is(":checked");

				var data = wn.slickgrid_tools.get_view_data(me.columns, me.dataView, 
					function(row, item) {
						if(with_groups) {
							// pad row
							for(var i=0; i<item.indent; i++) row[0] = "   " + row[0];
						}
						if(with_groups && item.group_or_ledger == "Group") return true;
						if(with_ledgers && item.group_or_ledger == "Ledger") return true;
					
						return false;
				});
				
				console.log(data);
				
				wn.downloadify(data, ["Report Manager", "System Manager"], me);
				return false;
			})

			return false;
		},
	})
	erpnext.trial_balance = new TrialBalance(wrapper, 'Trial Balance');
}