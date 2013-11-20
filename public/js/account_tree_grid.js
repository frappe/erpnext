// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

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

erpnext.AccountTreeGrid = wn.views.TreeGridReport.extend({
	init: function(wrapper, title) {
		this._super({
			title: title,
			page: wrapper,
			parent: $(wrapper).find('.layout-main'),
			appframe: wrapper.appframe,
			doctypes: ["Company", "Fiscal Year", "Account", "GL Entry", "Cost Center"],
			tree_grid: {
				show: true, 
				parent_field: "parent_account", 
				formatter: function(item) {
					return repl('<a href="#general-ledger/account=%(enc_value)s">%(value)s</a>', {
							value: item.name,
							enc_value: encodeURIComponent(item.name)
						});
				}
			},
		});
	},
	setup_columns: function() {
		this.columns = [
			{id: "name", name: wn._("Account"), field: "name", width: 300, cssClass: "cell-title", 
				formatter: this.tree_formatter},
			{id: "opening_debit", name: wn._("Opening (Dr)"), field: "opening_debit", width: 100,
				formatter: this.currency_formatter},
			{id: "opening_credit", name: wn._("Opening (Cr)"), field: "opening_credit", width: 100,
				formatter: this.currency_formatter},
			{id: "debit", name: wn._("Debit"), field: "debit", width: 100,
				formatter: this.currency_formatter},
			{id: "credit", name: wn._("Credit"), field: "credit", width: 100,
				formatter: this.currency_formatter},
			{id: "closing_debit", name: wn._("Closing (Dr)"), field: "closing_debit", width: 100,
				formatter: this.currency_formatter},
			{id: "closing_credit", name: wn._("Closing (Cr)"), field: "closing_credit", width: 100,
				formatter: this.currency_formatter}
		];

	},
	filters: [
		{fieldtype: "Select", label: wn._("Company"), link:"Company", default_value: "Select Company...",
			filter: function(val, item, opts, me) {
				if (item.company == val || val == opts.default_value) {
					return me.apply_zero_filter(val, item, opts, me);
				}
				return false;
			}},
		{fieldtype: "Select", label: wn._("Fiscal Year"), link:"Fiscal Year", 
			default_value: "Select Fiscal Year..."},
		{fieldtype: "Date", label: wn._("From Date")},
		{fieldtype: "Label", label: wn._("To")},
		{fieldtype: "Date", label: wn._("To Date")},
		{fieldtype: "Button", label: wn._("Refresh"), icon:"icon-refresh icon-white",
		 	cssClass:"btn-info"},
		{fieldtype: "Button", label: wn._("Reset Filters")},
	],
	setup_filters: function() {
		this._super();
		var me = this;
		// default filters
		this.filter_inputs.fiscal_year.change(function() {
			var fy = $(this).val();
			$.each(wn.report_dump.data["Fiscal Year"], function(i, v) {
				if (v.name==fy) {
					me.filter_inputs.from_date.val(dateutil.str_to_user(v.year_start_date));
					me.filter_inputs.to_date.val(dateutil.str_to_user(v.year_end_date));
				}
			});
			me.set_route();
		});
		me.show_zero_check()
		if(me.ignore_closing_entry) me.ignore_closing_entry();
	},
	prepare_data: function() {
		var me = this;
		if(!this.primary_data) {
			// make accounts list
			me.data = [];
			me.parent_map = {};
			me.item_by_name = {};

			$.each(wn.report_dump.data["Account"], function(i, v) {
				var d = copy_dict(v);

				me.data.push(d);
				me.item_by_name[d.name] = d;
				if(d.parent_account) {
					me.parent_map[d.name] = d.parent_account;
				}
			});
			
			me.primary_data = [].concat(me.data);
		}
		
		me.data = [].concat(me.primary_data);
		$.each(me.data, function(i, d) {
			me.init_account(d);
		});
		
		this.set_indent();
		this.prepare_balances();
		
	},
	init_account: function(d) {
		this.reset_item_values(d);	
	},

	prepare_balances: function() {
		var gl = wn.report_dump.data['GL Entry'];
		var me = this;

		this.opening_date = dateutil.user_to_obj(this.filter_inputs.from_date.val());
		this.closing_date = dateutil.user_to_obj(this.filter_inputs.to_date.val());
		this.set_fiscal_year();
		if (!this.fiscal_year) return;

		$.each(this.data, function(i, v) {
			v.opening_debit = v.opening_credit = v.debit 
				= v.credit = v.closing_debit = v.closing_credit = 0;
		});

		$.each(gl, function(i, v) {
			var posting_date = dateutil.str_to_obj(v.posting_date);
			var account = me.item_by_name[v.account];
			me.update_balances(account, posting_date, v);
		});

		this.update_groups();
	},
	update_balances: function(account, posting_date, v) {
		// opening
		if (posting_date < this.opening_date || v.is_opening === "Yes") {
			if (account.is_pl_account === "Yes" && 
				posting_date <= dateutil.str_to_obj(this.fiscal_year[1])) {
				// balance of previous fiscal_year should 
				//	not be part of opening of pl account balance
			} else {
				if(account.debit_or_credit=='Debit') {
					account.opening_debit += (v.debit - v.credit);
				} else {
					account.opening_credit += (v.credit - v.debit);
				}
			}
		} else if (this.opening_date <= posting_date && posting_date <= this.closing_date) {
			// in between
			account.debit += v.debit;
			account.credit += v.credit;
		}
		// closing
		if(account.debit_or_credit=='Debit') {
			account.closing_debit = account.opening_debit + account.debit - account.credit;
		} else {
			account.closing_credit = account.opening_credit - account.debit + account.credit;
		}
	},
	update_groups: function() {
		// update groups
		var me= this;
		$.each(this.data, function(i, account) {
			// update groups
			if((account.group_or_ledger == "Ledger") || (account.rgt - account.lft == 1)) {
				var parent = me.parent_map[account.name];
				while(parent) {
					var parent_account = me.item_by_name[parent];
					$.each(me.columns, function(c, col) {
						if (col.formatter == me.currency_formatter) {
							parent_account[col.field] = 
								flt(parent_account[col.field])
								+ flt(account[col.field]);
						}
					});
					parent = me.parent_map[parent];
				}				
			}
		});		
	},

	set_fiscal_year: function() {
		if (this.opening_date > this.closing_date) {
			msgprint(wn._("Opening Date should be before Closing Date"));
			return;
		}

		this.fiscal_year = null;
		var me = this;
		$.each(wn.report_dump.data["Fiscal Year"], function(i, v) {
			if (me.opening_date >= dateutil.str_to_obj(v.year_start_date) && 
				me.closing_date <= dateutil.str_to_obj(v.year_end_date)) {
					me.fiscal_year = v;
				}
		});

		if (!this.fiscal_year) {
			msgprint(wn._("Opening Date and Closing Date should be within same Fiscal Year"));
			return;
		}
	},
});