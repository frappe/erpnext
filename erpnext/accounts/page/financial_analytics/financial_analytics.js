// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.require("app/js/account_tree_grid.js");

wn.pages['financial-analytics'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: wn._('Financial Analytics'),
		single_column: true
	});
	erpnext.trial_balance = new erpnext.FinancialAnalytics(wrapper, 'Financial Analytics');
	wrapper.appframe.add_module_icon("Accounts")
	
}

erpnext.FinancialAnalytics = erpnext.AccountTreeGrid.extend({
	filters: [
		{fieldtype:"Select", label: wn._("PL or BS"), options:["Profit and Loss", "Balance Sheet"],
			filter: function(val, item, opts, me) {
				if(item._show) return true;
				
				// pl or bs
				var out = (val!='Balance Sheet') ? item.is_pl_account=='Yes' : item.is_pl_account!='Yes';
				if(!out) return false;
				
				return me.apply_zero_filter(val, item, opts, me);
			}},
		{fieldtype:"Select", label: wn._("Company"), link:"Company", default_value: "Select Company...",
			filter: function(val, item, opts) {
				return item.company == val || val == opts.default_value || item._show;
			}},
		{fieldtype:"Select", label: wn._("Fiscal Year"), link:"Fiscal Year", 
			default_value: "Select Fiscal Year..."},
		{fieldtype:"Date", label: wn._("From Date")},
		{fieldtype:"Label", label: wn._("To")},
		{fieldtype:"Date", label: wn._("To Date")},
		{fieldtype:"Select", label: wn._("Range"), 
			options:["Daily", "Weekly", "Monthly", "Quarterly", "Yearly"]},
		{fieldtype:"Button", label: wn._("Refresh"), icon:"icon-refresh icon-white"},
		{fieldtype:"Button", label: wn._("Reset Filters")}
	],
	setup_columns: function() {
		var std_columns = [
			{id: "check", name: wn._("Plot"), field: "check", width: 30,
				formatter: this.check_formatter},
			{id: "name", name: wn._("Account"), field: "name", width: 300,
				formatter: this.tree_formatter},
			{id: "opening", name: wn._("Opening"), field: "opening", hidden: true,
				formatter: this.currency_formatter}
		];
		
		this.make_date_range_columns();		
		this.columns = std_columns.concat(this.columns);
	},
	setup_filters: function() {
		var me = this;
		this._super();
		this.trigger_refresh_on_change(["pl_or_bs"]);
		
		this.filter_inputs.pl_or_bs
			.add_options($.map(wn.report_dump.data["Cost Center"], function(v) {return v.name;}));

		this.setup_plot_check();
	},
	init_filter_values: function() {
		this._super();
		this.filter_inputs.range.val('Monthly');
	},
	prepare_balances: function() {
		var me = this;
		
		// setup cost center map
		if(!this.cost_center_by_name) {
			this.cost_center_by_name = this.make_name_map(wn.report_dump.data["Cost Center"]);
		}
		
		var cost_center = inList(["Balance Sheet", "Profit and Loss"], this.pl_or_bs) 
			? null : this.cost_center_by_name[this.pl_or_bs];
		
		$.each(wn.report_dump.data['GL Entry'], function(i, gl) {
			var filter_by_cost_center = (function() {
				if(cost_center) {
					if(gl.cost_center) {
						var gl_cost_center = me.cost_center_by_name[gl.cost_center];
						return gl_cost_center.lft >= cost_center.lft && gl_cost_center.rgt <= cost_center.rgt;
					} else {
						return false;
					}
				} else {
					return true;
				}
			})();

			if(filter_by_cost_center) {
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
			}
		});

		// make balances as cumulative
		if(me.pl_or_bs=='Balance Sheet') {
			$.each(me.data, function(i, ac) {
				if((ac.rgt - ac.lft)==1 && ac.is_pl_account!='Yes') {
					var opening = 0;
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
		
		if(!me.is_default("company")) {
			// show Net Profit / Loss
			var net_profit = {
				company: me.company,
				id: "Net Profit / Loss",
				name: "Net Profit / Loss",
				indent: 0,
				opening: 0,
				checked: false,
				is_pl_account: me.pl_or_bs=="Balance Sheet" ? "No" : "Yes",
			};
			me.item_by_name[net_profit.name] = net_profit;

			$.each(me.data, function(i, ac) {
				if(!ac.parent_account && me.apply_filter(ac, "company")) {
					if(me.pl_or_bs == "Balance Sheet") {
						var valid_account = ac.is_pl_account!="Yes";
						var do_addition_for = "Debit";
					} else {
						var valid_account = ac.is_pl_account=="Yes";
						var do_addition_for = "Credit";
					}
					if(valid_account) {
						$.each(me.columns, function(i, col) {
							if(col.formatter==me.currency_formatter) {
								if(!net_profit[col.field]) net_profit[col.field] = 0;
								if(ac.debit_or_credit==do_addition_for) {
									net_profit[col.field] += ac[col.field];
								} else {
									net_profit[col.field] -= ac[col.field];
								}
							}
						});
					}
				}
			});

			this.data.push(net_profit);
		}
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
		var pl_or_bs = this.pl_or_bs;
		$.each(this.data, function(i, account) {
			
			var show = pl_or_bs != "Balance Sheet" ? account.is_pl_account=="Yes" : account.is_pl_account!="Yes";
			if (show && account.checked && me.apply_filter(account, "company")) {
				data.push({
					label: account.name,
					data: $.map(me.columns, function(col, idx) {
						if(col.formatter==me.currency_formatter && !col.hidden) {
							if (pl_or_bs != "Balance Sheet") {
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