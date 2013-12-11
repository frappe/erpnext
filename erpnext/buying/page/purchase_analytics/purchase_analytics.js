// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.pages['purchase-analytics'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: wn._('Purchase Analytics'),
		single_column: true
	});					
	
	new erpnext.PurchaseAnalytics(wrapper);
	

	wrapper.appframe.add_module_icon("Buying")
	
}

erpnext.PurchaseAnalytics = wn.views.TreeGridReport.extend({
	init: function(wrapper) {
		this._super({
			title: wn._("Purchase Analytics"),
			page: wrapper,
			parent: $(wrapper).find('.layout-main'),
			appframe: wrapper.appframe,
			doctypes: ["Item", "Item Group", "Supplier", "Supplier Type", "Company", "Fiscal Year", 
				"Purchase Invoice", "Purchase Invoice Item", 
				"Purchase Order", "Purchase Order Item[Purchase Analytics]", 
				"Purchase Receipt", "Purchase Receipt Item[Purchase Analytics]"],
			tree_grid: { show: true }
		});
		
		this.tree_grids = {
			"Supplier Type": {
				label: wn._("Supplier Type / Supplier"),
				show: true, 
				item_key: "supplier",
				parent_field: "parent_supplier_type", 
				formatter: function(item) {
					// return repl('<a href="#Report/stock-invoices/customer=%(enc_value)s">%(value)s</a>', {
					// 		value: item.name,
					// 		enc_value: encodeURIComponent(item.name)
					// 	});
					return item.name;
				}
			},
			"Supplier": {
				label: wn._("Supplier"),
				show: false, 
				item_key: "supplier",
				formatter: function(item) {
					return item.name;
				}
			},	
			"Item Group": {
				label: "Item",
				show: true, 
				parent_field: "parent_item_group", 
				item_key: "item_code",
				formatter: function(item) {
					return item.name;
				}
			},	
			"Item": {
				label: "Item",
				show: false, 
				item_key: "item_code",
				formatter: function(item) {
					return item.name;
				}
			},			
		}
	},
	setup_columns: function() {
		this.tree_grid = this.tree_grids[this.tree_type];

		var std_columns = [
			{id: "check", name: wn._("Plot"), field: "check", width: 30,
				formatter: this.check_formatter},
			{id: "name", name: this.tree_grid.label, field: "name", width: 300,
				formatter: this.tree_formatter},
			{id: "total", name: "Total", field: "total", plot: false,
				formatter: this.currency_formatter}
		];

		this.make_date_range_columns();		
		this.columns = std_columns.concat(this.columns);
	},
	filters: [
		{fieldtype:"Select", label: wn._("Tree Type"), options:["Supplier Type", "Supplier", 
			"Item Group", "Item"],
			filter: function(val, item, opts, me) {
				return me.apply_zero_filter(val, item, opts, me);
			}},
		{fieldtype:"Select", label: wn._("Based On"), options:["Purchase Invoice", 
			"Purchase Order", "Purchase Receipt"]},
		{fieldtype:"Select", label: wn._("Value or Qty"), options:["Value", "Quantity"]},
		{fieldtype:"Select", label: wn._("Company"), link:"Company", 
			default_value: "Select Company..."},
		{fieldtype:"Date", label: wn._("From Date")},
		{fieldtype:"Label", label: wn._("To")},
		{fieldtype:"Date", label: wn._("To Date")},
		{fieldtype:"Select", label: wn._("Range"), 
			options:["Daily", "Weekly", "Monthly", "Quarterly", "Yearly"]},
		{fieldtype:"Button", label: wn._("Refresh"), icon:"icon-refresh icon-white"},
		{fieldtype:"Button", label: wn._("Reset Filters")}
	],
	setup_filters: function() {
		var me = this;
		this._super();
		
		this.trigger_refresh_on_change(["value_or_qty", "tree_type", "based_on", "company"]);

		this.show_zero_check()		
		this.setup_plot_check();
	},
	init_filter_values: function() {
		this._super();
		this.filter_inputs.range.val('Monthly');
	},
	prepare_data: function() {
		var me = this;
		if (!this.tl) {
			// add 'Not Set' Supplier & Item
			// Add 'All Supplier Types' Supplier Type
			// (Supplier / Item are not mandatory!!)
			// Set parent supplier type for tree view
			
			$.each(wn.report_dump.data["Supplier Type"], function(i, v) {
				v['parent_supplier_type'] = "All Supplier Types"
			})
			
			wn.report_dump.data["Supplier Type"] = [{
				name: wn._("All Supplier Types"), 
				id: "All Supplier Types",
			}].concat(wn.report_dump.data["Supplier Type"]);
			
			wn.report_dump.data["Supplier"].push({
				name: wn._("Not Set"), 
				parent_supplier_type: "All Supplier Types",
				id: "Not Set",
			});

			wn.report_dump.data["Item"].push({
				name: wn._("Not Set"), 
				parent_item_group: "All Item Groups",
				id: "Not Set",
			});
		}
		
		if (!this.tl || !this.tl[this.based_on]) {
			this.make_transaction_list(this.based_on, this.based_on + " Item");
		}
		
		
		if(!this.data || me.item_type != me.tree_type) {
			if(me.tree_type=='Supplier') {
				var items = wn.report_dump.data["Supplier"];
			} if(me.tree_type=='Supplier Type') {
				var items = this.prepare_tree("Supplier", "Supplier Type");
			} else if(me.tree_type=="Item Group") {
				var items = this.prepare_tree("Item", "Item Group");
			} else if(me.tree_type=="Item") {
				var items = wn.report_dump.data["Item"];
			}

			me.item_type = me.tree_type
			me.parent_map = {};
			me.item_by_name = {};
			me.data = [];

			$.each(items, function(i, v) {
				var d = copy_dict(v);

				me.data.push(d);
				me.item_by_name[d.name] = d;
				if(d[me.tree_grid.parent_field]) {
					me.parent_map[d.name] = d[me.tree_grid.parent_field];
				}
				me.reset_item_values(d);
			});			
			
			this.set_indent();
			
		} else {
			// otherwise, only reset values
			$.each(this.data, function(i, d) {
				me.reset_item_values(d);
			});
		}
		
		this.prepare_balances();
		if(me.tree_grid.show) {
			this.set_totals(false);			
			this.update_groups();
		} else {
			this.set_totals(true);
		}
	},
	prepare_balances: function() {
		var me = this;
		var from_date = dateutil.str_to_obj(this.from_date);
		var to_date = dateutil.str_to_obj(this.to_date);
		var is_val = this.value_or_qty == 'Value';
		
		$.each(this.tl[this.based_on], function(i, tl) {
			if (me.is_default('company') ? true : tl.company === me.company) { 
				var posting_date = dateutil.str_to_obj(tl.posting_date);
				if (posting_date >= from_date && posting_date <= to_date) {
					var item = me.item_by_name[tl[me.tree_grid.item_key]] || 
						me.item_by_name['Not Set'];
					item[me.column_map[tl.posting_date].field] += (is_val ? tl.amount : tl.qty);
				}
			}
		});
	},
	update_groups: function() {
		var me = this;

		$.each(this.data, function(i, item) {
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
		});
	},
	set_totals: function(sort) {
		var me = this;
		var checked = false;
		$.each(this.data, function(i, d) { 
			d.total = 0.0;
			$.each(me.columns, function(i, col) {
				if(col.formatter==me.currency_formatter && !col.hidden && col.field!="total") 
					d.total += d[col.field];
				if(d.checked) checked = true;
			})
		});

		if(sort)this.data = this.data.sort(function(a, b) { return b.total - a.total; });

		if(!this.checked) {
			this.data[0].checked = true;
		}
	},
	get_plot_points: function(item, col, idx) {
		return [[dateutil.str_to_obj(col.id).getTime(), item[col.field]], 
			[dateutil.user_to_obj(col.name).getTime(), item[col.field]]];
	}
});