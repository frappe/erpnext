// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.require("assets/erpnext/js/stock_analytics.js");

frappe.pages['stock-balance'].onload = function(wrapper) { 
	frappe.ui.make_app_page({
		parent: wrapper,
		title: frappe._('Stock Balance'),
		single_column: true
	});
	
	new erpnext.StockBalance(wrapper);
	

	wrapper.appframe.add_module_icon("Stock")
	
}

erpnext.StockBalance = erpnext.StockAnalytics.extend({
	init: function(wrapper) {
		this._super(wrapper, {
			title: frappe._("Stock Balance"),
			doctypes: ["Item", "Item Group", "Warehouse", "Stock Ledger Entry", "Brand",
				"Stock Entry", "Project", "Serial No"],
		});
	},
	setup_columns: function() {
		this.columns = [
			{id: "name", name: frappe._("Item"), field: "name", width: 300,
				formatter: this.tree_formatter},
			{id: "item_name", name: frappe._("Item Name"), field: "item_name", width: 100},
			{id: "description", name: frappe._("Description"), field: "description", width: 200, 
				formatter: this.text_formatter},
			{id: "brand", name: frappe._("Brand"), field: "brand", width: 100},
			{id: "stock_uom", name: frappe._("UOM"), field: "stock_uom", width: 100},
			{id: "opening_qty", name: frappe._("Opening Qty"), field: "opening_qty", width: 100, 
				formatter: this.currency_formatter},
			{id: "inflow_qty", name: frappe._("In Qty"), field: "inflow_qty", width: 100, 
				formatter: this.currency_formatter},
			{id: "outflow_qty", name: frappe._("Out Qty"), field: "outflow_qty", width: 100, 
				formatter: this.currency_formatter},
			{id: "closing_qty", name: frappe._("Closing Qty"), field: "closing_qty", width: 100, 
				formatter: this.currency_formatter},
				
			{id: "opening_value", name: frappe._("Opening Value"), field: "opening_value", width: 100, 
				formatter: this.currency_formatter},
			{id: "inflow_value", name: frappe._("In Value"), field: "inflow_value", width: 100, 
				formatter: this.currency_formatter},
			{id: "outflow_value", name: frappe._("Out Value"), field: "outflow_value", width: 100, 
				formatter: this.currency_formatter},
			{id: "closing_value", name: frappe._("Closing Value"), field: "closing_value", width: 100, 
				formatter: this.currency_formatter},
		];
	},
	
	filters: [
		{fieldtype:"Select", label: frappe._("Brand"), link:"Brand", 
			default_value: "Select Brand...", filter: function(val, item, opts) {
				return val == opts.default_value || item.brand == val || item._show;
			}, link_formatter: {filter_input: "brand"}},
		{fieldtype:"Select", label: frappe._("Warehouse"), link:"Warehouse", 
			default_value: "Select Warehouse...", filter: function(val, item, opts, me) {
				return me.apply_zero_filter(val, item, opts, me);
			}},
		{fieldtype:"Select", label: frappe._("Project"), link:"Project", 
			default_value: "Select Project...", filter: function(val, item, opts, me) {
				return me.apply_zero_filter(val, item, opts, me);
			}, link_formatter: {filter_input: "project"}},
		{fieldtype:"Date", label: frappe._("From Date")},
		{fieldtype:"Label", label: frappe._("To")},
		{fieldtype:"Date", label: frappe._("To Date")},
		{fieldtype:"Button", label: frappe._("Refresh"), icon:"icon-refresh icon-white"},
		{fieldtype:"Button", label: frappe._("Reset Filters")}
	],
	
	setup_plot_check: function() {
		return;
	},
	
	prepare_data: function() {
		this.stock_entry_map = this.make_name_map(frappe.report_dump.data["Stock Entry"], "name");
		this._super();
	},
	
	prepare_balances: function() {
		var me = this;
		var from_date = dateutil.str_to_obj(this.from_date);
		var to_date = dateutil.str_to_obj(this.to_date);
		var data = frappe.report_dump.data["Stock Ledger Entry"];

		this.item_warehouse = {};
		this.serialized_buying_rates = this.get_serialized_buying_rates();

		for(var i=0, j=data.length; i<j; i++) {
			var sl = data[i];
			var sl_posting_date = dateutil.str_to_obj(sl.posting_date);
			
			if((me.is_default("warehouse") ? true : me.warehouse == sl.warehouse) &&
				(me.is_default("project") ? true : me.project == sl.project)) {
				var item = me.item_by_name[sl.item_code];
				var wh = me.get_item_warehouse(sl.warehouse, sl.item_code);
				var valuation_method = item.valuation_method ? 
					item.valuation_method : sys_defaults.valuation_method;
				var is_fifo = valuation_method == "FIFO";

				var qty_diff = sl.qty;
				var value_diff = me.get_value_diff(wh, sl, is_fifo);
				
				if(sl_posting_date < from_date) {
					item.opening_qty += qty_diff;
					item.opening_value += value_diff;
				} else if(sl_posting_date <= to_date) {
					var ignore_inflow_outflow = this.is_default("warehouse")
						&& sl.voucher_type=="Stock Entry" 
						&& this.stock_entry_map[sl.voucher_no].purpose=="Material Transfer";
					
					if(!ignore_inflow_outflow) {
						if(qty_diff < 0) {
							item.outflow_qty += Math.abs(qty_diff);
						} else {
							item.inflow_qty += qty_diff;
						}
						if(value_diff < 0) {
							item.outflow_value += Math.abs(value_diff);
						} else {
							item.inflow_value += value_diff;
						}
					
						item.closing_qty += qty_diff;
						item.closing_value += value_diff;
					}

				} else {
					break;
				}
			}
		}

		// opening + diff = closing
		// adding opening, since diff already added to closing		
		$.each(me.item_by_name, function(key, item) {
			item.closing_qty += item.opening_qty;
			item.closing_value += item.opening_value;
		});
	},
	
	update_groups: function() {
		var me = this;

		$.each(this.data, function(i, item) {
			// update groups
			if(!item.is_group && me.apply_filter(item, "brand")) {
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
					
					// show parent if filtered by brand
					if(item.brand == me.brand)
						parent_group._show = true;
					
					parent = me.parent_map[parent];
				}
			}
		});
	},
	
	get_plot_data: function() {
		return;
	}
});