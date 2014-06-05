// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.require("assets/erpnext/js/account_tree_grid.js");

frappe.pages['trial-balance'].onload = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Trial Balance'),
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
						__("With period closing entry") + '</div>')
					.appendTo(me.wrapper)
					.find("input").click(function() { me.refresh(); });
			});
		},

		prepare_balances: function() {
			// store value of with closing entry
			this.with_period_closing_entry = this.wrapper
				.find(".with_period_closing_entry input:checked").length;
			this._super();
			this.add_total_debit_credit();
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

		add_total_debit_credit: function() {
			var me = this;

			var total_row = {
				company: me.company,
				id: "Total Debit / Credit",
				name: "Total Debit / Credit",
				indent: 0,
				opening_dr: "NA",
				opening_cr: "NA",
				debit: 0,
				credit: 0,
				checked: false,
			};
			me.item_by_name[total_row.name] = total_row;

			$.each(this.data, function(i, account) {
				if((account.group_or_ledger == "Ledger") || (account.rgt - account.lft == 1)) {
					total_row["debit"] += account.debit;
					total_row["credit"] += account.credit;
				}
			});

			this.data.push(total_row);
		}
	})
	erpnext.trial_balance = new TrialBalance(wrapper, 'Trial Balance');


	wrapper.appframe.add_module_icon("Accounts")

}
