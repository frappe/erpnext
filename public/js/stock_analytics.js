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
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

wn.require("app/js/stock_grid_report.js");

erpnext.StockAnalytics = erpnext.StockGridReport.extend({
	init: function(wrapper, opts) {
		var args = {
			title: "Stock Analytics",
			page: wrapper,
			parent: $(wrapper).find('.layout-main'),
			appframe: wrapper.appframe,
			doctypes: ["Item", "Item Group", "Warehouse", "Stock Ledger Entry", "Brand", 
				"Fiscal Year"],
			tree_grid: {
				show: true, 
				parent_field: "parent_item_group", 
				formatter: function(item) {
					if(!item.is_group) {
						return repl('<a href="#stock-ledger/item_code=%(enc_value)s">%(value)s</a>',
							{
								value: item.name,
								enc_value: encodeURIComponent(item.name)
							});
					} else {
						return item.name;
					}
					
				}
			},
		}
		
		if(opts) $.extend(args, opts);
		
		this._super(args);
	},
	setup_columns: function() {
		var std_columns = [
			{id: "check", name: "Plot", field: "check", width: 30,
				formatter: this.check_formatter},
			{id: "name", name: "Item", field: "name", width: 300,
				formatter: this.tree_formatter},
			{id: "brand", name: "Brand", field: "brand", width: 100},
			{id: "stock_uom", name: "UOM", field: "stock_uom", width: 100},
			{id: "opening", name: "Opening", field: "opening", hidden: true,
				formatter: this.currency_formatter}
		];

		this.make_date_range_columns();
		this.columns = std_columns.concat(this.columns);
	},
	filters: [
		{fieldtype:"Select", label: "Value or Qty", options:["Value", "Quantity"],
			filter: function(val, item, opts, me) {
				return me.apply_zero_filter(val, item, opts, me);
			}},
		{fieldtype:"Select", label: "Brand", link:"Brand", 
			default_value: "Select Brand...", filter: function(val, item, opts) {
				return val == opts.default_value || item.brand == val || item._show;
			}, link_formatter: {filter_input: "brand"}},
		{fieldtype:"Select", label: "Warehouse", link:"Warehouse", 
			default_value: "Select Warehouse..."},
		{fieldtype:"Date", label: "From Date"},
		{fieldtype:"Label", label: "To"},
		{fieldtype:"Date", label: "To Date"},
		{fieldtype:"Select", label: "Range", 
			options:["Daily", "Weekly", "Monthly", "Quarterly", "Yearly"]},
		{fieldtype:"Button", label: "Refresh", icon:"icon-refresh icon-white", cssClass:"btn-info"},
		{fieldtype:"Button", label: "Reset Filters"}
	],
	setup_filters: function() {
		var me = this;
		this._super();
		
		this.trigger_refresh_on_change(["value_or_qty", "brand", "warehouse", "range"]);

		this.show_zero_check();
		this.setup_plot_check();
	},
	init_filter_values: function() {
		this._super();
		this.filter_inputs.range && this.filter_inputs.range.val('Monthly');
	},
	prepare_data: function() {
		var me = this;
				
		if(!this.data) {
			var items = this.prepare_tree("Item", "Item Group");

			me.parent_map = {};
			me.item_by_name = {};
			me.data = [];

			$.each(items, function(i, v) {
				var d = copy_dict(v);

				me.data.push(d);
				me.item_by_name[d.name] = d;
				if(d.parent_item_group) {
					me.parent_map[d.name] = d.parent_item_group;
				}
				me.reset_item_values(d);
			});
			this.set_indent();
			this.data[0].checked = true;
		} else {
			// otherwise, only reset values
			$.each(this.data, function(i, d) {
				me.reset_item_values(d);
			});
		}
		
		this.prepare_balances();
		this.update_groups();
		
	},
	prepare_balances: function() {
		var me = this;
		var from_date = dateutil.str_to_obj(this.from_date);
		var to_date = dateutil.str_to_obj(this.to_date);
		var data = wn.report_dump.data["Stock Ledger Entry"];

		this.item_warehouse = {};
		this.serialized_buying_rates = this.get_serialized_buying_rates();

		for(var i=0, j=data.length; i<j; i++) {
			var sl = data[i];
			sl.posting_datetime = sl.posting_date + " " + sl.posting_time;
			var posting_datetime = dateutil.str_to_obj(sl.posting_datetime);
			
			if(me.is_default("warehouse") ? true : me.warehouse == sl.warehouse) {
				var item = me.item_by_name[sl.item_code];
				
				if(me.value_or_qty!="Quantity") {
					var wh = me.get_item_warehouse(sl.warehouse, sl.item_code);
					var valuation_method = item.valuation_method ? 
						item.valuation_method : sys_defaults.valuation_method;
					var is_fifo = valuation_method == "FIFO";
					
					var diff = me.get_value_diff(wh, sl, is_fifo);
				} else {
					var diff = sl.qty;
				}

				if(posting_datetime < from_date) {
					item.opening += diff;
				} else if(posting_datetime <= to_date) {
					item[me.column_map[sl.posting_date].field] += diff;
				} else {
					break;
				}
				
				me.round_item_values(item);
			}
		}
	},
	update_groups: function() {
		var me = this;

		$.each(this.data, function(i, item) {
			// update groups
			if(!item.is_group && me.apply_filter(item, "brand")) {
				var balance = item.opening;
				$.each(me.columns, function(i, col) {
					if(col.formatter==me.currency_formatter && !col.hidden) {
						item[col.field] = balance + item[col.field];
						balance = item[col.field];
					}
				});
				
				var parent = me.parent_map[item.name];
				while(parent) {
					parent_group = me.item_by_name[parent];
					$.each(me.columns, function(c, col) {
						if (col.formatter == me.currency_formatter) {
							parent_group[col.field] = 
								flt(parent_group[col.field])
								+ flt(item[col.field]);
						}
					});
					parent = me.parent_map[parent];
				}
			}
		});
	},
	get_plot_points: function(item, col, idx) {
		return [[dateutil.user_to_obj(col.name).getTime(), item[col.field]]]
	}
});