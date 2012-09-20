wn.pages['stock-analytics'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: 'Stock Analytics',
		single_column: true
	});
	
	new erpnext.StockAnalytics(wrapper);
}

erpnext.StockAnalytics = wn.views.GridReportWithPlot.extend({
	init: function(wrapper) {
		this._super({
			title: "Stock Analytics",
			page: wrapper,
			parent: $(wrapper).find('.layout-main'),
			appframe: wrapper.appframe,
			doctypes: ["Item", "Item Group", "Warehouse", "Stock Ledger Entry", "Fiscal Year"],
			tree_grid: {
				show: true, 
				parent_field: "parent_item_group", 
				formatter: function(item) {
					return repl('<a href="#stock-ledger/item=%(enc_value)s">%(value)s</a>', {
							value: item.name,
							enc_value: encodeURIComponent(item.name)
						});
				}
			}			
		})
	},
	setup_columns: function() {
		var std_columns = [
			{id: "check", name: "Plot", field: "check", width: 30,
				formatter: this.check_formatter},
			{id: "name", name: "Item", field: "name", width: 300,
				formatter: this.tree_formatter, doctype: "Item"},
			{id: "opening", name: "Opening", field: "opening", hidden: true,
				formatter: this.currency_formatter},
			{id: "balance_qty", name: "Balance Qty", field: "balance_qty", hidden: true,
				formatter: this.currency_formatter},
			{id: "balance_value", name: "Balance Value", field: "balance_value", hidden: true,
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
		{fieldtype:"Select", label: "Warehouse", link:"Warehouse", 
			default_value: "Select Warehouse..."},
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
	setup_filters: function() {
		var me = this;
		this._super();

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
		
		this.filter_inputs.value_or_qty.change(function() {
			me.filter_inputs.refresh.click();
		});

		this.show_zero_check()		
		this.setup_plot_check();
	},
	init_filter_values: function() {
		this._super();
		this.filter_inputs.range.val('Weekly');
	},
	prepare_data: function() {
		var me = this;
		
		if(!this.data) {
			var items = this.get_item_tree();

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
		} else {
			// otherwise, only reset values
			$.each(this.data, function(i, d) {
				me.reset_item_values(d);
			});
		}
		
		this.prepare_balances();
		this.update_groups();
		
	},
	get_item_tree: function() {
		// prepare map with items in respective item group
		var item_group_map = {};
		$.each(wn.report_dump.data["Item"], function(i, item) {
			var parent = item.parent_item_group
			if(!item_group_map[parent]) item_group_map[parent] = [];
			item_group_map[parent].push(item);
		});
		
		// arrange items besides their parent item groups
		var items = [];
		$.each(wn.report_dump.data["Item Group"], function(i, group){
			group.is_group = true;
			items.push(group);
			items = items.concat(item_group_map[group.name] || []);
		});
		return items;
	},
	prepare_balances: function() {
		var me = this;
		var from_date = dateutil.str_to_obj(this.from_date);
		var to_date = dateutil.str_to_obj(this.to_date);
		var data = wn.report_dump.data["Stock Ledger Entry"];
		var is_value = me.value_or_qty == "Value";
				
		for(var i=0, j=data.length; i<j; i++) {
			var sl = data[i];
			sl.posting_datetime = sl.posting_date + " " + sl.posting_time;
			var posting_datetime = dateutil.str_to_obj(sl.posting_datetime);
			
			if(me.is_default("warehouse") ? true : me.warehouse == sl.warehouse) {			
				var item = me.item_by_name[sl.item_code];

				// value
				var rate = sl.qty > 0 ? sl.incoming_rate :
					(item.balance_qty.toFixed(2) == 0.00 ? 0 : flt(item.balance_value) / flt(item.balance_qty));
				var value_diff = (rate * sl.qty);
								
				// update balance
				item.balance_qty += sl.qty;
				item.balance_value += value_diff;

				var diff = is_value ? value_diff : sl.qty;

				if(posting_datetime < from_date) {
					item.opening += diff;
				} else if(posting_datetime <= to_date) {
					item[me.column_map[sl.posting_date].field] += diff;
				} else {
					break;
				}
			}
		}
	},
	update_groups: function() {
		var me = this;

		$.each(this.data, function(i, item) {
			// update groups
			if(!item.is_group) {
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
	get_plot_data: function() {
		var data = [];
		var me = this;
		$.each(this.data, function(i, item) {
			if (item.checked) {
				data.push({
					label: item.name,
					data: $.map(me.columns, function(col, idx) {
						if(col.formatter==me.currency_formatter && !col.hidden) {
							return [[dateutil.user_to_obj(col.name).getTime(), item[col.field]]]
						}
					}),
					points: {show: true},
					lines: {show: true, fill: true},
				});
				
				// prepend opening 
				data[data.length-1].data = [[dateutil.str_to_obj(me.from_date).getTime(), 
					item.opening]].concat(data[data.length-1].data);
			}
		});
	
		return data;
	},
	get_plot_options: function() {
		return {
			grid: { hoverable: true, clickable: true },
			xaxis: { mode: "time", 
				min: dateutil.str_to_obj(this.from_date).getTime(),
				max: dateutil.str_to_obj(this.to_date).getTime() }
		}
	}
});
