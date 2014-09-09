// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


frappe.pages['stock-ageing'].onload = function(wrapper) { 
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Stock Ageing'),
		single_column: true
	});

	new erpnext.StockAgeing(wrapper);
	

	wrapper.appframe.add_module_icon("Stock")
	
}

frappe.require("assets/erpnext/js/stock_grid_report.js");

erpnext.StockAgeing = erpnext.StockGridReport.extend({
	init: function(wrapper) {
		this._super({
			title: __("Stock Ageing"),
			page: wrapper,
			parent: $(wrapper).find('.layout-main'),
			appframe: wrapper.appframe,
			doctypes: ["Item", "Warehouse", "Stock Ledger Entry", "Item Group", "Brand", "Serial No"],
		})
	},
	setup_columns: function() {
		this.columns = [
			{id: "name", name: __("Item"), field: "name", width: 300,
				link_formatter: {
					open_btn: true,
					doctype: '"Item"'
				}},
			{id: "item_name", name: __("Item Name"), field: "item_name", 
				width: 100, formatter: this.text_formatter},
			{id: "description", name: __("Description"), field: "description", 
				width: 200, formatter: this.text_formatter},
			{id: "brand", name: __("Brand"), field: "brand", width: 100},
			{id: "average_age", name: __("Average Age"), field: "average_age",
				formatter: this.currency_formatter},
			{id: "earliest", name: __("Earliest"), field: "earliest",
				formatter: this.currency_formatter},
			{id: "latest", name: __("Latest"), field: "latest",
				formatter: this.currency_formatter},
			{id: "stock_uom", name: "UOM", field: "stock_uom", width: 100},
		];
	},
	filters: [
		{fieldtype:"Select", label: __("Warehouse"), link:"Warehouse", 
			default_value: "Select Warehouse..."},
		{fieldtype:"Select", label: __("Brand"), link:"Brand", 
			default_value: "Select Brand...", filter: function(val, item, opts) {
				return val == opts.default_value || item.brand == val;
			}, link_formatter: {filter_input: "brand"}},
		{fieldtype:"Select", label: __("Plot By"), 
			options: ["Average Age", "Earliest", "Latest"]},
		{fieldtype:"Date", label: __("To Date")},
		{fieldtype:"Button", label: __("Refresh"), icon:"icon-refresh icon-white"},
		{fieldtype:"Button", label: __("Reset Filters"), icon: "icon-filter"}
	],
	setup_filters: function() {
		var me = this;
		this._super();
		this.trigger_refresh_on_change(["warehouse", "plot_by", "brand"]);
		this.show_zero_check();
	},
	init_filter_values: function() {
		this._super();
		this.filter_inputs.to_date.val(dateutil.obj_to_user(new Date()));
	},
	prepare_data: function() {
		var me = this;
				
		if(!this.data) {
			me._data = frappe.report_dump.data["Item"];
			me.item_by_name = me.make_name_map(me._data);
		}
		
		this.data = [].concat(this._data);
		
		this.serialized_buying_rates = this.get_serialized_buying_rates();
		
		$.each(this.data, function(i, d) {
			me.reset_item_values(d);
		});
		
		this.prepare_balances();
		
		// filter out brand
		this.data = $.map(this.data, function(d) {
			return me.apply_filter(d, "brand") ? d : null;
		});
		
		// filter out rows with zero values
		this.data = $.map(this.data, function(d) {
			return me.apply_zero_filter(null, d, null, me) ? d : null;
		});
	},
	prepare_balances: function() {
		var me = this;
		var to_date = dateutil.str_to_obj(this.to_date);
		var data = frappe.report_dump.data["Stock Ledger Entry"];

		this.item_warehouse = {};

		for(var i=0, j=data.length; i<j; i++) {
			var sl = data[i];
			var posting_date = dateutil.str_to_obj(sl.posting_date);
			
			if(me.is_default("warehouse") ? true : me.warehouse == sl.warehouse) {
				var wh = me.get_item_warehouse(sl.warehouse, sl.item_code);
				
				// call diff to build fifo stack in item_warehouse
				var diff = me.get_value_diff(wh, sl, true);

				if(posting_date > to_date) 
					break;
			}
		}
		
		$.each(me.data, function(i, item) {
			var full_fifo_stack = [];
			if(me.is_default("warehouse")) {
				$.each(me.item_warehouse[item.name] || {}, function(i, wh) {
					full_fifo_stack = full_fifo_stack.concat(wh.fifo_stack || [])
				});
			} else {
				full_fifo_stack = me.get_item_warehouse(me.warehouse, item.name).fifo_stack || [];
			}
			
			var age_qty = total_qty = 0.0;
			var min_age = max_age = null;
			
			$.each(full_fifo_stack, function(i, batch) {
				var batch_age = dateutil.get_diff(me.to_date, batch[2]);
				age_qty += batch_age * batch[0];
				total_qty += batch[0];
				max_age = Math.max(max_age, batch_age);
				if(min_age===null) min_age=batch_age;
				else min_age = Math.min(min_age, batch_age);
			});
			
			item.average_age = total_qty.toFixed(2)==0.0 ? 0 
				: (age_qty / total_qty).toFixed(2);
			item.earliest = max_age || 0.0;
			item.latest = min_age || 0.0;
		});
		
		this.data = this.data.sort(function(a, b) { 
			var sort_by = me.plot_by.replace(" ", "_").toLowerCase();
			return b[sort_by] - a[sort_by]; 
		});
	},
	get_plot_data: function() {
		var data = [];
		var me = this;

		data.push({
			label: me.plot_by,
			data: $.map(me.data, function(item, idx) {
				return [[idx+1, item[me.plot_by.replace(" ", "_").toLowerCase() ]]]
			}),
			bars: {show: true},
		});
				
		return data.length ? data : false;
	},
	get_plot_options: function() {
		var me = this;
		return {
			grid: { hoverable: true, clickable: true },
			xaxis: {  
				ticks: $.map(me.data, function(item, idx) { return [[idx+1, item.name]] }),
				max: 15
			},
			series: { downsample: { threshold: 1000 } }
		}
	}	
});