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
wn.require("js/app/account_tree_grid.css");

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
			filter: function(val, item, opts) {
				if(val=='Profit and Loss') {
					return item.is_pl_account=='Yes' || item._show;
				} else {
					return item.is_pl_account=='No' || item._show;
				}
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
		this.columns = [
			{id: "check", name: "Plot", field: "check", width: 30,
				formatter: function(row, cell, value, columnDef, dataContext) {					
					return repl("<input type='checkbox' account='%(name)s' \
						class='plot-check' %(checked)s>", {
							"name": dataContext.name,
							"checked": dataContext.checked ? "checked" : ""
						})
				}},
			{id: "name", name: "Account", field: "name", width: 300,
				formatter: this.account_formatter},
		];
		
		var me = this;
		var range = this.filter_inputs.range.val();
		this.from_date = dateutil.user_to_str(this.filter_inputs.from_date.val());
		this.to_date = dateutil.user_to_str(this.filter_inputs.to_date.val());
		var date_diff = dateutil.get_diff(this.to_date, this.from_date);
			
		me.column_map = {};	
		var build_columns = function(condition) {
			for(var i=0; i < date_diff; i++) {
				var date = dateutil.add_days(me.from_date, i);
				if(!condition) condition = function() { return true; }
				
				if(condition(date)) {
					me.columns.push({
						from_date: date,
						id: date,
						name: dateutil.str_to_user(date),
						field: date,
						formatter: me.currency_formatter,
						width: 100
					});					
				}
				me.last_date = date;
				me.column_map[date] = me.columns[me.columns.length-1];
			}
		}
		
		if(range=='Daily') {
			build_columns();
		} else if(range=='Weekly') {
			build_columns(function(date) {
				if(!me.last_date) return true;
				return !(dateutil.get_diff(date, me.from_date) % 7)
			});		
		} else if(range=='Monthly') {
			build_columns(function(date) {
				if(!me.last_date) return true;
				return dateutil.str_to_obj(me.last_date).getMonth() != dateutil.str_to_obj(date).getMonth()
			});
		} else if(range=='Quarterly') {
			build_columns(function(date) {
				if(!me.last_date) return true;
				return dateutil.str_to_obj(date).getDate()==1 && in_list([0,3,6,9], dateutil.str_to_obj(date).getMonth())
			});			
		} else if(range=='Yearly') {
			build_columns(function(date) {
				if(!me.last_date) return true;	
				return $.map(wn.report_dump.data['Fiscal Year'], function(v) { 
						return date==v.year_start_date ? true : null;
					}).length;
			});
		}
		
	},
	init_filter_values: function() {
		this._super();
		this.filter_inputs.range.val('Weekly');
	},
	prepare_balances: function() {
		var me = this;
		
		$.each(wn.report_dump.data['GL Entry'], function(i, gl) {
			var posting_date = dateutil.str_to_obj(gl.posting_date);
			var account = me.accounts_by_name[gl.account];
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
			$.each(me.accounts, function(i, ac) {
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
	},
	add_balance: function(field, account, gl) {
		account[field] = flt(account[field]) + 
			((account.debit_or_credit == "Debit" ? 1 : -1) * (gl.debit - gl.credit))
	},
	init_account: function(d) {
		var me = this;
		$.each(this.columns, function(i, col) {
			if (col.formatter==me.currency_formatter) {
				d[col.from_date] = 0;
			}
		});
	},
	init_refresh: function() {
		var me = this;
		$.each(this.accounts || [], function(i, account) {
			account.checked && me.preset_checks.push(account.name);
		});
	},
	init_plot: function() {
		var me = this;
		if(this.preset_checks.length) {
			$.each(me.preset_checks, function(i, name) {
				me.accounts_by_name[name].checked = true;
			});
		} else {
			$.each(this.accounts, function(i, account) {
				if(!account.parent_account) {
					account.checked = true;
				}
			});
		}
	},
	get_plot_data: function() {
		var data = [];
		var me = this;
		var pl_or_bs = this.filter_inputs.pl_or_bs.val();
		$.each(this.accounts, function(i, account) {
			var show = pl_or_bs == "Profit and Loss" ? account.is_pl_account=="Yes" : account.is_pl_account!="Yes";
			if (show && account.checked) {
				data.push({
					label: account.name,
					data: $.map(me.columns, function(col, idx) {
						if(col.formatter==me.currency_formatter)
							return [[idx, account[col.field]]]
					})
				});
			}
		});
	
		return data;
	},
	add_grid_events: function() {
		this._super();
		var me = this;
		this.wrapper.find('.plot-check').click(function() {
			var checked = $(this).attr("checked");
			me.accounts_by_name[$(this).attr("account")].checked = checked ? true : false;
			me.render_plot();
		});
	}
})