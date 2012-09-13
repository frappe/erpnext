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
	erpnext.coa.company_select = wrapper.appframe.add_select("Company", ["Loading..."]);
	erpnext.coa.opening_date = wrapper.appframe.add_date("Opening Date")
		.val(dateutil.str_to_user(sys_defaults.year_start_date));
	erpnext.coa.closing_date = wrapper.appframe.add_date("Closing Date")
		.val(dateutil.obj_to_user(new Date()));
	
	erpnext.coa.waiting = $('<div class="well" style="width: 63%; margin: 30px auto;">\
		<p style="text-align: center;">Building Trial Balance Report. \
			Please wait for a few moments</p>\
		<div class="progress progress-striped active">\
			<div class="bar" style="width: 100%"></div></div>')
		.appendTo($(wrapper).find('.layout-main'));
	
	$('<div id="chart-of-accounts" style="height: 500px; border: 1px solid #aaa;">\
		</div>').appendTo($(wrapper).find('.layout-main'));
	
	wn.call({
		module: "accounts",
		page: "chart_of_accounts",
		method: "get_companies",
		callback: function(r) {
			erpnext.coa.waiting.toggle();
			erpnext.coa.company_select.empty().add_options(r.message.companies).change();
			erpnext.coa.fiscal_years = r.message.fiscal_years;
		}
	});
	
	erpnext.coa.company_select.change(function() {
		erpnext.coa.load_slickgrid();
		erpnext.coa.load_data($(this).val());
	});
	
	erpnext.coa.opening_date.change(erpnext.coa.refresh);
	erpnext.coa.closing_date.change(erpnext.coa.refresh);
}

erpnext.coa = {
	load_slickgrid: function() {
		// load tree
		wn.require('js/lib/jquery/jquery.ui.sortable');
		wn.require('js/lib/slickgrid/slick.grid.css');
		wn.require('js/lib/slickgrid/slick-default-theme.css');
		wn.require('js/lib/slickgrid/jquery.event.drag.min.js');
		wn.require('js/lib/slickgrid/slick.core.js');
		wn.require('js/lib/slickgrid/slick.formatters.js');
		wn.require('js/lib/slickgrid/slick.grid.js');
		wn.require('js/lib/slickgrid/slick.dataview.js');
		wn.dom.set_style('.slick-cell { font-size: 12px; }');		
	},
	refresh: function() {
		erpnext.coa.prepare_balances();
		erpnext.coa.render();
	},
	load_data: function(company) {
		wn.call({
			module: "accounts",
			page: "chart_of_accounts",
			method: "get_chart",
			args: {company: company},
			callback: function(r) {
				erpnext.coa.gl = r.message.gl;
				erpnext.coa.prepare_chart(r.message.chart);
				erpnext.coa.prepare_balances();
				erpnext.coa.render();
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
					"opening": 0,
					"debit": 0,
					"credit": 0,
					"closing": 0,
					"debit_or_credit": v[2],
					"is_pl": v[3]
				};

				data.push(d);
				data_by_name[d.name] = d;
				if(d.parent) {
					parent_map[d.name] = d.parent;
				}		
			}
		});
		erpnext.coa.set_indent(data, parent_map);
		erpnext.coa.data = data;
		erpnext.coa.parent_map = parent_map;
		erpnext.coa.data_by_name = data_by_name;
	},
	prepare_balances: function() {
		var gl = erpnext.coa.gl;
		var opening_date = dateutil.user_to_obj(erpnext.coa.opening_date.val());
		var closing_date = dateutil.user_to_obj(erpnext.coa.closing_date.val());
		var fiscal_year = erpnext.coa.get_fiscal_year(opening_date, closing_date);
		if (!fiscal_year) return;
		
		$.each(erpnext.coa.data, function(i, v) {
			v.opening = v.debit = v.credit = v.closing = 0;
		});
		
		$.each(gl, function(i, v) {
			var posting_date = dateutil.str_to_obj(v[0]);
			var account = erpnext.coa.data_by_name[v[1]];
			// opening
			if (posting_date < opening_date || v[4] === "Yes") {
				if (account.is_pl === "Yes" && posting_date <= dateutil.str_to_obj(fiscal_year[1])) {
					// balance of previous fiscal_year should 
					//	not be part of opening of pl account balance
				} else {
					if (account.debit_or_credit === "Debit") {
						account.opening += (v[2] - v[3]);
					} else {
						account.opening += (v[3] - v[2]);
					}
				}
			} else if (opening_date <= posting_date && posting_date <= closing_date) {
				// in between
				account.debit += v[2];
				account.credit += v[3];
			}
			// closing
			if (account.debit_or_credit === "Debit") {
				account.closing = account.opening + account.debit - account.credit;
			} else {
				account.closing = account.opening + account.credit - account.debit;
			}
		});
		
		// format amount
		$.each(erpnext.coa.data, function(i, v) {
			v.opening = fmt_money(v.opening);
			v.debit = fmt_money(v.debit);
			v.credit = fmt_money(v.credit);
			v.closing = fmt_money(v.closing);
		});
	},
	get_fiscal_year: function(opening_date, closing_date) {
		if (opening_date > closing_date) {
			msgprint("Opening Date should be before Closing Date");
			return;
		}
		
		var fiscal_year = null;
		$.each(erpnext.coa.fiscal_years, function(i, v) {
			if (opening_date >= dateutil.str_to_obj(v[1]) && 
				closing_date <= dateutil.str_to_obj(v[2])) {
					fiscal_year = v;
				}
		});
		
		if (!fiscal_year) {
			msgprint("Opening Date and Closing Date should be within same Fiscal Year");
			return;
		}
		return fiscal_year;
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
	render: function() {
		erpnext.coa.waiting.toggle(false);

		// initialize the model
		erpnext.coa.dataView = new Slick.Data.DataView({ inlineFilters: true });
		erpnext.coa.dataView.beginUpdate();
		erpnext.coa.dataView.setItems(erpnext.coa.data);
		erpnext.coa.dataView.setFilter(erpnext.coa.filter)
		erpnext.coa.dataView.endUpdate();

		var columns = [
			{id: "name", name: "Account", field: "name", width: 400, cssClass: "cell-title", 
				formatter: erpnext.coa.account_formatter},
			{id: "opening", name: "Opening", field: "opening"},
			{id: "debit", name: "Debit", field: "debit"},
			{id: "credit", name: "Credit", field: "credit"},
			{id: "closing", name: "Closing", field: "closing"}			
		];
		
		var options = {
			editable: false,
			enableColumnReorder: false
		};

		// initialize the grid
		var grid = new Slick.Grid("#chart-of-accounts", erpnext.coa.dataView, columns, options);
		erpnext.coa.add_events(grid);
		erpnext.coa.grid = grid;
	},
	add_events: function(grid) {
		grid.onClick.subscribe(function (e, args) {
			if ($(e.target).hasClass("toggle")) {
				var item = erpnext.coa.dataView.getItem(args.row);
				if (item) {
					if (!item._collapsed) {
						item._collapsed = true;
					} else {
						item._collapsed = false;
					}

					erpnext.coa.dataView.updateItem(item.id, item);
				}
				e.stopImmediatePropagation();
			}
		});

		erpnext.coa.dataView.onRowsChanged.subscribe(function (e, args) {
			grid.invalidateRows(args.rows);
			grid.render();
		});
		
		erpnext.coa.dataView.onRowCountChanged.subscribe(function (e, args) {
			grid.updateRowCount();
			grid.render();
		});
		
	},
	filter: function(item) {
		if (item.parent) {
			var parent = item.parent;
			while (parent) {
				if (erpnext.coa.data_by_name[parent]._collapsed) {
					return false;
				}
				parent = erpnext.coa.parent_map[parent];
			}
		}
		return true;
	},
	account_formatter: function (row, cell, value, columnDef, dataContext) {
		value = value.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
		var data = erpnext.coa.data;
		var spacer = "<span style='display:inline-block;height:1px;width:" + 
			(15 * dataContext["indent"]) + "px'></span>";
		var idx = erpnext.coa.dataView.getIdxById(dataContext.id);
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
}
