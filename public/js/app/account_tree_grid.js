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

erpnext.AccountTreeGrid = wn.views.GridReport.extend({
	init: function(wrapper, title) {
		this._super({
			title: title,
			page: wrapper,
			parent: $(wrapper).find('.layout-main'),
			appframe: wrapper.appframe,
			doctypes: ["Company", "Fiscal Year", "Account", "GL Entry"]
		});
	},
	setup_columns: function() {
		this.columns = [
			{id: "name", name: "Account", field: "name", width: 300, cssClass: "cell-title", 
				formatter: this.account_formatter},
			{id: "opening_debit", name: "Opening (Dr)", field: "opening_debit", width: 100,
				formatter: this.currency_formatter},
			{id: "opening_credit", name: "Opening (Cr)", field: "opening_credit", width: 100,
				formatter: this.currency_formatter},
			{id: "debit", name: "Debit", field: "debit", width: 100,
				formatter: this.currency_formatter},
			{id: "credit", name: "Credit", field: "credit", width: 100,
				formatter: this.currency_formatter},
			{id: "closing_debit", name: "Closing (Dr)", field: "closing_debit", width: 100,
				formatter: this.currency_formatter},
			{id: "closing_credit", name: "Closing (Cr)", field: "closing_credit", width: 100,
				formatter: this.currency_formatter}
		];

	},
	filters: [
		{fieldtype:"Select", label: "Company", link:"Company", default_value: "Select Company...",
			filter: function(val, item, opts) {
				return item.company == val || val == opts.default_value || item._show;
			}},
		{fieldtype:"Select", label: "Fiscal Year", link:"Fiscal Year", 
			default_value: "Select Fiscal Year..."},
		{fieldtype:"Date", label: "From Date"},
		{fieldtype:"Label", label: "To"},
		{fieldtype:"Date", label: "To Date"},
		{fieldtype:"Button", label: "Refresh", icon:"icon-refresh icon-white", cssClass:"btn-info"},
		{fieldtype:"Button", label: "Reset Filters"}
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
	},
	init_filter_values: function() {
		this.filter_inputs.company.val(sys_defaults.company);
		this.filter_inputs.fiscal_year.val(sys_defaults.fiscal_year);
		this.filter_inputs.from_date.val(dateutil.str_to_user(sys_defaults.year_start_date));
		this.filter_inputs.to_date.val(dateutil.str_to_user(sys_defaults.year_end_date));
	},
	prepare_data: function() {
		var me = this;
		var data = [];
		var parent_map = {};
		var data_by_name = {};
		$.each(wn.report_dump.data["Account"], function(i, v) {
			var d = copy_dict(v);
			me.init_account(d);

			data.push(d);
			data_by_name[d.name] = d;
			if(d.parent_account) {
				parent_map[d.name] = d.parent_account;
			}
		});
		this.set_indent(data, parent_map);
		this.accounts = data;
		this.parent_map = parent_map;
		this.accounts_by_name = data_by_name;
		this.prepare_balances();
		this.prepare_data_view(this.accounts);
	},
	init_account: function(d) {
		$.extend(d, {
			"opening_debit": 0,
			"opening_credit": 0,
			"debit": 0,
			"credit": 0,
			"closing_debit": 0,
			"closing_credit": 0				
		});
	},
	prepare_balances: function() {
		var gl = wn.report_dump.data['GL Entry'];
		var me = this;

		this.opening_date = dateutil.user_to_obj(this.filter_inputs.from_date.val());
		this.closing_date = dateutil.user_to_obj(this.filter_inputs.to_date.val());
		this.set_fiscal_year();
		if (!this.fiscal_year) return;

		$.each(this.accounts, function(i, v) {
			v.opening_debit = v.opening_credit = v.debit 
				= v.credit = v.closing_debit = v.closing_credit = 0;
		});

		$.each(gl, function(i, v) {
			var posting_date = dateutil.str_to_obj(v.posting_date);
			var account = me.accounts_by_name[v.account];
			me.update_balances(account, posting_date, v)
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
		$.each(this.accounts, function(i, account) {
			// update groups
			var parent = me.parent_map[account.name];
			while(parent) {
				parent_account = me.accounts_by_name[parent];
				$.each(me.columns, function(c, col) {
					if (col.formatter == me.currency_formatter) {
						parent_account[col.field] += account[col.field];
					}
				});
				parent = me.parent_map[parent];
			}			
		});		
	},

	set_fiscal_year: function() {
		if (this.opening_date > this.closing_date) {
			msgprint("Opening Date should be before Closing Date");
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
			msgprint("Opening Date and Closing Date should be within same Fiscal Year");
			return;
		}
	},
	set_indent: function(data, parent_map) {
		$.each(data, function(i, d) {
			var indent = 0;
			var parent = parent_map[d.name];
			if(parent) {
				while(parent) {
					indent++;
					parent = parent_map[parent];
				}				
			}
			d.indent = indent;
		});
	},
	account_formatter: function (row, cell, value, columnDef, dataContext) {
		value = value.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
		var data = wn.cur_grid_report.accounts;
		var spacer = "<span style='display:inline-block;height:1px;width:" + 
			(15 * dataContext["indent"]) + "px'></span>";
		var idx = wn.cur_grid_report.dataView.getIdxById(dataContext.id);
		var account_link = repl('<a href="#general-ledger/account=%(enc_value)s">%(value)s</a>', {
				value: value,
				enc_value: encodeURIComponent(value)
			});
			
		if (data[idx + 1] && data[idx + 1].indent > data[idx].indent) {
			if (dataContext._collapsed) {
				return spacer + " <span class='toggle expand'></span>&nbsp;" + account_link;
			} else {
				return spacer + " <span class='toggle collapse'></span>&nbsp;" + account_link;
			}
		} else {
			return spacer + " <span class='toggle'></span>&nbsp;" + account_link;
		}
	},
	add_grid_events: function() {
		var me = this;
		this.grid.onClick.subscribe(function (e, args) {
			if ($(e.target).hasClass("toggle")) {
				var item = me.dataView.getItem(args.row);
				if (item) {
					if (!item._collapsed) {
						item._collapsed = true;
					} else {
						item._collapsed = false;
					}

					me.dataView.updateItem(item.id, item);
				}
				e.stopImmediatePropagation();
			}
		});
	},
	custom_dataview_filter: function(item) {
		if (item.parent_account) {
			var parent = item.parent_account;
			while (parent) {
				if (wn.cur_grid_report.accounts_by_name[parent]._collapsed) {
					return false;
				}
				parent = wn.cur_grid_report.parent_map[parent];
			}
		}
		return true;
	}		
});