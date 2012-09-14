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

/* todo
 	- load / display chart of accounts
	- settings for company, start date, end data
	- load balances
	- open ledger on link
*/

wn.pages['chart-of-accounts'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: 'Chart of Accounts',
		single_column: true
	});
	
	erpnext.coa.make_page(wrapper);
	erpnext.coa.load_companies();
}
erpnext.coa = {
	make_page: function(wrapper) {
		erpnext.coa.company_select = wrapper.appframe
			.add_select("Company", ["Loading..."])
			.change(function() {
				erpnext.coa.chart = new erpnext.ChartOfAccounts();
			});
			
		erpnext.coa.fiscal_year_select = wrapper.appframe
			.add_select("Fiscal Year", ["Loading..."]).css("width", "100px")
			.change(function() {
				var selected_year = $(this).val();
				var fiscal_year = $.map(erpnext.coa.fiscal_years, function(v) {
					return v[0] === selected_year ? v : null;
				});
				erpnext.coa.opening_date.val(dateutil.str_to_user(fiscal_year[1]));
				erpnext.coa.closing_date.val(dateutil.str_to_user(fiscal_year[2]));
				erpnext.coa.refresh_btn.click();
			})

		erpnext.coa.opening_date = wrapper.appframe.add_date("Opening Date")
			.val(dateutil.str_to_user(sys_defaults.year_start_date));

		var end_date = new Date();
		if(end_date > dateutil.str_to_obj(sys_defaults.year_end_date)) 
			end_date = sys_defaults.year_end_date;
			
		erpnext.coa.closing_date = wrapper.appframe.add_date("Closing Date")
			.val(dateutil.obj_to_user(end_date));

		erpnext.coa.refresh_btn = wrapper.appframe.add_button("Refresh", function() {
			erpnext.coa.chart.refresh();
		}, "icon-refresh");



		erpnext.coa.waiting = $('<div class="well" style="width: 63%; margin: 30px auto;">\
			<p style="text-align: center;">Building Trial Balance Report. \
				Please wait for a few moments</p>\
			<div class="progress progress-striped active">\
				<div class="bar" style="width: 100%"></div></div>')
			.appendTo($(wrapper).find('.layout-main'));

		$('<div id="chart-of-accounts" style="height: 500px; border: 1px solid #aaa;">\
			</div>').appendTo($(wrapper).find('.layout-main'));	
			
	},
	load_companies: function() {
		wn.call({
			module: "accounts",
			page: "chart_of_accounts",
			method: "get_companies",
			callback: function(r) {
				erpnext.coa.waiting.toggle();
				erpnext.coa.company_select.empty().add_options(r.message.companies)
					.val(sys_defaults.company || r.message.companies[0]).change();
				erpnext.coa.fiscal_year_select.empty()
					.add_options($.map(r.message.fiscal_years, function(v) { return v[0]; }))
					.val(sys_defaults.fiscal_year);
				erpnext.coa.fiscal_years = r.message.fiscal_years;
			}
		});		
	}
};

erpnext.ChartOfAccounts = Class.extend({
	init: function() {
		this.load_slickgrid();
		this.load_data($(erpnext.coa.company_select).val());
	},
	load_slickgrid: function() {
		// load tree
		wn.require('js/lib/slickgrid/slick.grid.css');
		wn.require('js/lib/slickgrid/slick-default-theme.css');
		wn.require('js/lib/slickgrid/jquery.event.drag.min.js');
		wn.require('js/lib/slickgrid/slick.core.js');
		wn.require('js/lib/slickgrid/slick.grid.js');
		wn.require('js/lib/slickgrid/slick.dataview.js');
		wn.dom.set_style('.slick-cell { font-size: 12px; }');
	},
	refresh: function() {
		this.prepare_balances();
		this.render();
	},
	render: function() {
		var me = this;
		erpnext.coa.waiting.toggle(false);
		this.setup_dataview();

		var columns = [
			{id: "name", name: "Account", field: "name", width: 300, cssClass: "cell-title", 
				formatter: this.account_formatter},
			{id: "opening_debit", name: "Opening (Dr)", field: "opening_debit", width: 100},
			{id: "opening_credit", name: "Opening (Cr)", field: "opening_credit", width: 100},
			{id: "debit", name: "Debit", field: "debit", width: 100},
			{id: "credit", name: "Credit", field: "credit", width: 100},
			{id: "closing_debit", name: "Closing (Dr)", field: "closing_debit", width: 100},
			{id: "closing_credit", name: "Closing (Cr)", field: "closing_credit", width: 100}
		];
		
		var options = {
			editable: false,
			enableColumnReorder: false
		};

		// initialize the grid
		var grid = new Slick.Grid("#chart-of-accounts", this.dataView, columns, options);
		this.add_events(grid);
		this.grid = grid;
	},	
	load_data: function(company) {
		var me = this;
		wn.call({
			module: "accounts",
			page: "chart_of_accounts",
			method: "get_chart",
			args: {company: company},
			callback: function(r) {
				me.gl = r.message.gl;
				me.prepare_chart(r.message.chart);
				$.each(me.gl, function(i, v) {
					v[1] = me.accounts[v[1]].name;
				});
				me.refresh();
			}
		})
	},
	prepare_chart: function(indata) {
		var data = [];
		var parent_map = {};
		var data_by_name = {};
		$.each(indata, function(i, v) {
			if(v[0]) {
				var d = {
					"id": v[0],
					"name": v[0],
					"parent": v[1],
					"debit_or_credit": v[2],
					"opening_debit": 0,
					"opening_credit": 0,
					"debit": 0,
					"credit": 0,
					"closing_debit": 0,
					"closing_credit": 0,
					"is_pl": v[3]
				};
				
				data.push(d);
				data_by_name[d.name] = d;
				if(d.parent) {
					parent_map[d.name] = d.parent;
				}
			}
		});
		this.set_indent(data, parent_map);
		this.accounts = data;
		this.parent_map = parent_map;
		this.accounts_by_name = data_by_name;
	},
	prepare_balances: function() {
		var gl = this.gl;
		var me = this;
		
		this.opening_date = dateutil.user_to_obj(erpnext.coa.opening_date.val());
		this.closing_date = dateutil.user_to_obj(erpnext.coa.closing_date.val());
		this.set_fiscal_year();
		if (!this.fiscal_year) return;
		
		$.each(this.accounts, function(i, v) {
			v.opening_debit = v.opening_credit = v.debit 
				= v.credit = v.closing_debit = v.closing_credit = 0;
		});
		
		$.each(gl, function(i, v) {
			var posting_date = dateutil.str_to_obj(v[0]);
			var account = me.accounts_by_name[v[1]];
			me.update_balances(account, posting_date, v)
		});
		
		this.update_groups();
		this.format_balances();
	},
	update_balances: function(account, posting_date, v) {
		// opening
		if (posting_date < this.opening_date || v[4] === "Y") {
			if (account.is_pl === "Yes" && posting_date <= dateutil.str_to_obj(this.fiscal_year[1])) {
				// balance of previous fiscal_year should 
				//	not be part of opening of pl account balance
			} else {
				if(account.debit_or_credit=='D') {
					account.opening_debit += (v[2] - v[3]);
				} else {
					account.opening_credit += (v[3] - v[2]);
				}
			}
		} else if (this.opening_date <= posting_date && posting_date <= this.closing_date) {
			// in between
			account.debit += v[2];
			account.credit += v[3];
		}
		// closing
		if(account.debit_or_credit=='D') {
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
				parent_account.opening_debit += account.opening_debit;
				parent_account.opening_credit += account.opening_credit;
				parent_account.debit += account.debit;
				parent_account.credit += account.credit;
				parent_account.closing_debit += account.closing_debit;
				parent_account.closing_credit += account.closing_credit;
				parent = me.parent_map[parent];
			}			
		});		
	},
	format_balances: function() {
		// format amount
		$.each(this.accounts, function(i, v) {
			v.opening_debit = fmt_money(v.opening_debit);
			v.opening_credit = fmt_money(v.opening_credit);
			v.debit = fmt_money(v.debit);
			v.credit = fmt_money(v.credit);
			v.closing_debit = fmt_money(v.closing_debit);
			v.closing_credit = fmt_money(v.closing_credit);
		});		
	},
	set_fiscal_year: function() {
		if (this.opening_date > this.closing_date) {
			msgprint("Opening Date should be before Closing Date");
			return;
		}
			
		this.fiscal_year = null;
		var me = this;
		$.each(erpnext.coa.fiscal_years, function(i, v) {
			if (me.opening_date >= dateutil.str_to_obj(v[1]) && 
				me.closing_date <= dateutil.str_to_obj(v[2])) {
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
	setup_dataview: function() {
		var me = this;
		// initialize the model
		this.dataView = new Slick.Data.DataView({ inlineFilters: true });
		this.dataView.beginUpdate();
		this.dataView.setItems(this.accounts);
		this.dataView.setFilter(this.dataview_filter);
		this.dataView.endUpdate();
	},
	dataview_filter: function(item) {
		if (item.parent) {
			var parent = item.parent;
			while (parent) {
				if (erpnext.coa.chart.accounts_by_name[parent]._collapsed) {
					return false;
				}
				parent = erpnext.coa.chart.parent_map[parent];
			}
		}
		return true;
	},
	add_events: function(grid) {
		var me = this;
		grid.onClick.subscribe(function (e, args) {
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

		this.dataView.onRowsChanged.subscribe(function (e, args) {
			grid.invalidateRows(args.rows);
			grid.render();
		});
		
		this.dataView.onRowCountChanged.subscribe(function (e, args) {
			grid.updateRowCount();
			grid.render();
		});
		
	},
	account_formatter: function (row, cell, value, columnDef, dataContext) {
		value = value.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
		var data = erpnext.coa.chart.accounts;
		var spacer = "<span style='display:inline-block;height:1px;width:" + 
			(15 * dataContext["indent"]) + "px'></span>";
		var idx = erpnext.coa.chart.dataView.getIdxById(dataContext.id);
		if (data[idx + 1] && data[idx + 1].indent > data[idx].indent) {
			if (dataContext._collapsed) {
				return spacer + " <span class='toggle expand'></span>&nbsp;" + value;
			} else {
				return spacer + " <span class='toggle collapse'></span>&nbsp;" + value;
			}
		} else {
			return spacer + " <span class='toggle'></span>&nbsp;" + value;
		}
	}
});
