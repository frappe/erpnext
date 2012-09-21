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

wn.require("js/app/account_tree_grid.js");

wn.pages['financial-analytics'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: 'Financial Analytics',
		single_column: true
	});
	erpnext.trial_balance = new erpnext.FinancialAnalytics(wrapper, 'Financial Analytics');
}

erpnext.FinancialAnalytics = erpnext.AccountTreeGrid.extend({
	filters: [
		{fieldtype:"Select", label: "PL or BS", options:["Profit and Loss", "Balance Sheet"],
			filter: function(val, item, opts, me) {
				if(item._show) return true;
				
				// pl or bs
				var out = (val=='Profit and Loss') ? item.is_pl_account=='Yes' : item.is_pl_account!='Yes';
				if(!out) return false;
				
				return me.apply_zero_filter(val, item, opts, me);
			}},
		{fieldtype:"Select", label: "Company", link:"Company", default_value: "Select Company...",
			filter: function(val, item, opts) {
				return item.company == val || val == opts.default_value || item._show;
			}},
		{fieldtype:"Select", label: "Fiscal Year", link:"Fiscal Year", 
			default_value: "Select Fiscal Year..."},
		{fieldtype:"Date", label: "From Date"},
		{fieldtype:"Label", label: "To"},
		{fieldtype:"Date", label: "To Date"},
		{fieldtype:"Select", label: "Range", 
			options:["Daily", "Weekly", "Monthly", "Quarterly", "Yearly"]},
		{fieldtype:"Button", label: "Refresh", icon:"icon-refresh icon-white", cssClass:"btn-info"},
		{fieldtype:"Button", label: "Reset Filters"}
	],
	setup_columns: function() {
		var std_columns = [
			{id: "check", name: "Plot", field: "check", width: 30,
				formatter: this.check_formatter},
			{id: "name", name: "Account", field: "name", width: 300,
				formatter: this.tree_formatter},
			{id: "opening", name: "Opening", field: "opening", hidden: true,
				formatter: this.currency_formatter}
		];
		
		this.make_date_range_columns();		
		this.columns = std_columns.concat(this.columns);
	},
	setup_filters: function() {
		var me = this;
		this._super();
		this.filter_inputs.pl_or_bs.change(function() {
			me.filter_inputs.refresh.click();
		});
		this.setup_plot_check();
	},
	init_filter_values: function() {
		this._super();
		this.filter_inputs.range.val('Weekly');
	},
	prepare_balances: function() {
		var me = this;
		
		$.each(wn.report_dump.data['GL Entry'], function(i, gl) {
			var posting_date = dateutil.str_to_obj(gl.posting_date);
			var account = me.item_by_name[gl.account];
			var col = me.column_map[gl.posting_date];
			
			if(col) {
				if(gl.voucher_type=='Period Closing Voucher') {
					// period closing voucher not to be added
					// to profit and loss accounts (else will become zero!!)
					if(account.is_pl_account!='Yes')
						me.add_balance(col.field, account, gl);
				} else {
					me.add_balance(col.field, account, gl);
				}
				
			} else if(account.is_pl_account!='Yes' 
				&& (posting_date < dateutil.str_to_obj(me.from_date))) {
				me.add_balance('opening', account, gl);
			}
		});

		// make balances as cumulative
		if(me.filter_inputs.pl_or_bs.val()=='Balance Sheet') {
			$.each(me.data, function(i, ac) {
				if((ac.rgt - ac.lft)==1 && ac.is_pl_account!='Yes') {
					var opening = flt(ac.opening);
					//if(opening) throw opening;
					$.each(me.columns, function(i, col) {
						if(col.formatter==me.currency_formatter) {
							ac[col.field] = opening + flt(ac[col.field]);
							opening = ac[col.field];
						}
					});					
				}
			})
		}
		this.update_groups();
		this.accounts_initialized = true;
	},
	add_balance: function(field, account, gl) {
		account[field] = flt(account[field]) + 
			((account.debit_or_credit == "Debit" ? 1 : -1) * (flt(gl.debit) - flt(gl.credit)))
	},
	init_account: function(d) {
		// set 0 values for all columns
		this.reset_item_values(d);
		
		// check for default graphs
		if(!this.accounts_initialized && !d.parent_account) {
			d.checked = true;
		}
		
	},
	get_plot_data: function() {
		var data = [];
		var me = this;
		var pl_or_bs = this.filter_inputs.pl_or_bs.val();
		$.each(this.data, function(i, account) {
			var show = pl_or_bs == "Profit and Loss" ? account.is_pl_account=="Yes" : account.is_pl_account!="Yes";
			if (show && account.checked && me.apply_filter(account, "company")) {
				data.push({
					label: account.name,
					data: $.map(me.columns, function(col, idx) {
						if(col.formatter==me.currency_formatter && !col.hidden) {
							if (pl_or_bs == "Profit and Loss") {
								return [[dateutil.str_to_obj(col.id).getTime(), account[col.field]], 
									[dateutil.user_to_obj(col.name).getTime(), account[col.field]]];
							} else {
								return [[dateutil.user_to_obj(col.name).getTime(), account[col.field]]];
							}							
						}
					}),
					points: {show: true},
					lines: {show: true, fill: true},
				});
				
				if(pl_or_bs == "Balance Sheet") {
					// prepend opening for balance sheet accounts
					data[data.length-1].data = [[dateutil.str_to_obj(me.from_date).getTime(), 
						account.opening]].concat(data[data.length-1].data);
				}
			}
		});
	
		return data;
	}
})