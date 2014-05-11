// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.require("app/js/account_tree_grid.js");

wn.pages['trial-balance'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: wn._('Trial Balance'),
		single_column: true
	});
	var TrialBalance = erpnext.AccountTreeGrid.extend({
		init: function(wrapper, title) {
			var me = this;
			this._super(wrapper, title);
			
			// period closing entry checkbox
			this.wrapper.bind("make", function() {
				$('<div style="margin: 10px 0px; "\
				 	class="with_period_closing_entry"><input type="checkbox" checked="checked">' + 
						wn._("With period closing entry") + '</div>')
					.appendTo(me.wrapper)
					.find("input").click(function() { me.refresh(); });
			});
		},
		
		prepare_balances: function() {
			// store value of with closing entry
			this.with_period_closing_entry = this.wrapper
				.find(".with_period_closing_entry input:checked").length;
			this._super();
		},
		
		update_balances: function(account, posting_date, v) {
			// for period closing voucher, 
			// only consider them when adding "With Closing Entry is checked"
			if(v.voucher_type === "Period Closing Voucher") {
				if(this.with_period_closing_entry) {
					this._super(account, posting_date, v);
				}
			} else {
				this._super(account, posting_date, v);
			}
		},
	})
	erpnext.trial_balance = new TrialBalance(wrapper, 'Trial Balance');
	

	wrapper.appframe.add_module_icon("Accounts")
	
}