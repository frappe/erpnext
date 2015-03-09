// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.pages['financial-analytics'].on_page_load = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Financial Analytics'),
		single_column: true
	});
	erpnext.financial_analytics = new erpnext.FinancialAnalytics(wrapper, 'Financial Analytics');
	frappe.breadcrumbs.add("Accounts");

};

frappe.require("assets/erpnext/js/account_tree_grid.js");

erpnext.FinancialAnalytics = erpnext.AccountTreeGrid.extend({
	filters: [
		{
			fieldtype:"Select", label: __("PL or BS"), fieldname: "pl_or_bs",
			options:[{"label": __("Profit and Loss"), "value": "Profit and Loss"},
				{"label": __("Balance Sheet"), "value": "Balance Sheet"}],
			filter: function(val, item, opts, me) {
				if(item._show) return true;

				// pl or bs
				var out = (val=='Balance Sheet') ?
					item.report_type=='Balance Sheet' : item.report_type=='Profit and Loss';
				if(!out) return false;

				return me.apply_zero_filter(val, item, opts, me);
			}
		},
		{
			fieldtype:"Select", label: __("Company"), fieldname: "company",
			link:"Company", default_value: __("Select Company..."),
			filter: function(val, item, opts) {
				return item.company == val || val == opts.default_value || item._show;
			}
		},
		{fieldtype:"Select", label: __("Fiscal Year"), link:"Fiscal Year", fieldname: "fiscal_year",
			default_value: __("Select Fiscal Year...")},
		{fieldtype:"Date", label: __("From Date"), fieldname: "from_date"},
		{fieldtype:"Date", label: __("To Date"), fieldname: "to_date"},
		{fieldtype:"Select", label: __("Range"), fieldname: "range",
			options:[{label: __("Daily"), value: "Daily"}, {label: __("Weekly"), value: "Weekly"},
				{label: __("Monthly"), value: "Monthly"}, {label: __("Quarterly"), value: "Quarterly"},
		{label: __("Yearly"), value: "Yearly"}]}
	],
	setup_columns: function() {
		var std_columns = [
			{id: "_check", name: __("Plot"), field: "_check", width: 30,
				formatter: this.check_formatter},
			{id: "name", name: __("Account"), field: "name", width: 300,
				formatter: this.tree_formatter},
			{id: "opening_dr", name: __("Opening (Dr)"), field: "opening_dr",
				hidden: true, formatter: this.currency_formatter, balance_type: "Dr"},
			{id: "opening_cr", name: __("Opening (Cr)"), field: "opening_cr",
				hidden: true, formatter: this.currency_formatter, balance_type: "Cr"},
		];

		this.make_date_range_columns(true);
		this.columns = std_columns.concat(this.columns);
	},
	make_date_range_columns: function() {
		this.columns = [];

		var me = this;
		var range = this.filter_inputs.range.val();
		this.from_date = dateutil.user_to_str(this.filter_inputs.from_date.val());
		this.to_date = dateutil.user_to_str(this.filter_inputs.to_date.val());
		var date_diff = dateutil.get_diff(this.to_date, this.from_date);

		me.column_map = {};
		me.last_date = null;

		var add_column = function(date, balance_type) {
			me.columns.push({
				id: date + "_" + balance_type.toLowerCase(),
				name: dateutil.str_to_user(date),
				field: date + "_" + balance_type.toLowerCase(),
				date: date,
				balance_type: balance_type,
				formatter: me.currency_formatter,
				width: 110
			});
		}

		var build_columns = function(condition) {
			// add column for each date range
			for(var i=0; i <= date_diff; i++) {
				var date = dateutil.add_days(me.from_date, i);
				if(!condition) condition = function() { return true; }

				if(condition(date)) {
					$.each(["Dr", "Cr"], function(i, v) {
						add_column(date, v)
					});
				}
				me.last_date = date;

				if(me.columns.length) {
					me.column_map[date] = me.columns[me.columns.length-1];
				}
			}
		}

		// make columns for all date ranges
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
				return $.map(frappe.report_dump.data['Fiscal Year'], function(v) {
						return date==v.year_start_date ? true : null;
					}).length;
			});

		}

		// set label as last date of period
		$.each(this.columns, function(i, col) {
			col.name = me.columns[i+2]
				? dateutil.str_to_user(dateutil.add_days(me.columns[i+2].date, -1)) + " (" + me.columns[i].balance_type + ")"
				: dateutil.str_to_user(me.to_date) + " (" + me.columns[i].balance_type + ")";
		});
	},
	setup_filters: function() {
		var me = this;
		this._super();
		this.trigger_refresh_on_change(["pl_or_bs"]);

		this.filter_inputs.pl_or_bs
			.add_options($.map(frappe.report_dump.data["Cost Center"], function(v) {return v.name;}));

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
			this.cost_center_by_name = this.make_name_map(frappe.report_dump.data["Cost Center"]);
		}

		var cost_center = inList(["Balance Sheet", "Profit and Loss"], this.pl_or_bs)
			? null : this.cost_center_by_name[this.pl_or_bs];

		$.each(frappe.report_dump.data['GL Entry'], function(i, gl) {
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
						if(account.report_type=='Balance Sheet')
							me.add_balance(col.date, account, gl);
					} else {
						me.add_balance(col.date, account, gl);
					}

				} else if(account.report_type=='Balance Sheet'
					&& (posting_date < dateutil.str_to_obj(me.from_date))) {
						me.add_balance('opening', account, gl);
				}
			}
		});

		// make balances as cumulative
		if(me.pl_or_bs=='Balance Sheet') {
			$.each(me.data, function(i, ac) {
				if((ac.rgt - ac.lft)==1 && ac.report_type=='Balance Sheet') {
					var opening = flt(ac["opening_dr"]) - flt(ac["opening_cr"]);
					//if(opening) throw opening;
					$.each(me.columns, function(i, col) {
						if(col.formatter==me.currency_formatter) {
							if(col.balance_type=="Dr" && !in_list(["opening_dr", "opening_cr"], col.field)) {
								opening = opening + flt(ac[col.date + "_dr"]) -
									flt(ac[col.date + "_cr"]);
								me.set_debit_or_credit(ac, col.date, opening);
							}
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
				report_type: me.pl_or_bs=="Balance Sheet"? "Balance Sheet" : "Profit and Loss",
			};
			me.item_by_name[net_profit.name] = net_profit;

			$.each(me.columns, function(i, col) {
				if(col.formatter==me.currency_formatter) {
					if(!net_profit[col.id]) net_profit[col.id] = 0;
				}
			});

			$.each(me.data, function(i, ac) {
				if(!ac.parent_account && me.apply_filter(ac, "company") &&
						ac.report_type==net_profit.report_type) {
					$.each(me.columns, function(i, col) {
						if(col.formatter==me.currency_formatter && col.balance_type=="Dr") {
							var bal = net_profit[col.date+"_dr"] -
								net_profit[col.date+"_cr"] +
								ac[col.date+"_dr"] - ac[col.date+"_cr"];
							me.set_debit_or_credit(net_profit, col.date, bal);
						}
					});
				}
			});
			this.data.push(net_profit);
		}
	},
	add_balance: function(field, account, gl) {
		var bal = flt(account[field+"_dr"]) - flt(account[field+"_cr"]) +
			flt(gl.debit) - flt(gl.credit);
		this.set_debit_or_credit(account, field, bal);
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
						if (col.formatter == me.currency_formatter && col.balance_type=="Dr") {
							var bal = flt(parent_account[col.date+"_dr"]) -
								flt(parent_account[col.date+"_cr"]) +
								flt(account[col.date+"_dr"]) -
								flt(account[col.date+"_cr"]);
							me.set_debit_or_credit(parent_account, col.date, bal);
						}
					});
					parent = me.parent_map[parent];
				}
			}
		});
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

			var show = pl_or_bs == "Balance Sheet" ?
				account.report_type=="Balance Sheet" : account.report_type=="Profit and Loss";
			if (show && account.checked && me.apply_filter(account, "company")) {
				data.push({
					label: account.name,
					data: $.map(me.columns, function(col, idx) {
						if(col.formatter==me.currency_formatter && !col.hidden &&
							col.balance_type=="Dr") {
								var bal = account[col.date+"_dr"]||account[col.date+"_cr"];
								if (pl_or_bs != "Balance Sheet") {
									return [[dateutil.str_to_obj(col.date).getTime(), bal],
										[dateutil.str_to_obj(col.date).getTime(), bal]];
								} else {
									return [[dateutil.str_to_obj(col.date).getTime(), bal]];
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
