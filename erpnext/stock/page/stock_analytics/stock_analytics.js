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
			},		
		})
	},
	setup_columns: function() {
		var std_columns = [
			{id: "check", name: "Plot", field: "check", width: 30,
				formatter: this.check_formatter},
			{id: "name", name: "Item", field: "name", width: 300,
				formatter: this.tree_formatter, doctype: "Item"},
			{id: "opening", name: "Opening", field: "opening", hidden: true,
				formatter: this.currency_formatter}
		];

		this.make_date_range_columns();		
		this.columns = std_columns.concat(this.columns);
	},
	filters: [
		{fieldtype:"Select", label: "Value or Qty", options:["Value (Weighted Average)", "Value (FIFO)", "Quantity"],
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

		var warehouse_item = {};
		var get_warehouse_item = function(warehouse, item) {
			if(!warehouse_item[warehouse]) warehouse_item[warehouse] = {};
			if(!warehouse_item[warehouse][item]) warehouse_item[warehouse][item] = {
				balance_qty: 0.0, balance_value: 0.0, fifo_stack: []
			};
			return warehouse_item[warehouse][item];
		}
				
		for(var i=0, j=data.length; i<j; i++) {
			var sl = data[i];
			sl.posting_datetime = sl.posting_date + " " + sl.posting_time;
			var posting_datetime = dateutil.str_to_obj(sl.posting_datetime);
			
			if(me.is_default("warehouse") ? true : me.warehouse == sl.warehouse) {			
				var item = me.item_by_name[sl.item_code];
				
				if(me.value_or_qty!="Quantity") {
					var wh = get_warehouse_item(sl.warehouse, sl.item_code);
					var diff = me.get_value_diff(wh, sl);
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
			}
		}
	},
	get_value_diff: function(wh, sl) {
		var is_fifo = this.value_or_qty== "Value (FIFO)";
				
		// value
		if(sl.qty > 0) {
			// incoming - rate is given
			var rate = sl.incoming_rate;	
			var add_qty = sl.qty;
			if(wh.balance_qty < 0) {
				// negative valuation
				// only add value of quantity if
				// the balance goes above 0
				add_qty = wh.balance_qty + sl.qty;
				if(add_qty < 0) {
					add_qty = 0;
				}
			}
			var value_diff = (rate * add_qty);
			
			if(add_qty)
				wh.fifo_stack.push([add_qty, sl.incoming_rate]);					
		} else {
			// outgoing
						
			if(is_fifo)	{
				var value_diff = this.get_fifo_value_diff(wh, sl);				
			} else {
				// average rate for weighted average
				var rate = (wh.balance_qty.toFixed(2) == 0.00 ? 0 : 
					flt(wh.balance_value) / flt(wh.balance_qty));
				
				// no change in value if negative qty
				if((wh.balance_qty + sl.qty).toFixed(2) >= 0.00)
					var value_diff = (rate * sl.qty);			
				else 
					var value_diff = -wh.balance_value;
			}
		}

		// update balance (only needed in case of valuation)
		wh.balance_qty += sl.qty;
		wh.balance_value += value_diff;

		if(sl.item_code=="0.5Motor") {
			console.log([sl.voucher_no, sl.qty, sl.warehouse, value_diff]);
			console.log(wh.fifo_stack);			
		}
		
		return value_diff;
	},
	get_fifo_value_diff: function(wh, sl) {
		// get exact rate from fifo stack
		var fifo_stack = wh.fifo_stack.reverse();
		var fifo_value_diff = 0.0;
		var qty = -sl.qty;
		
		for(var i=0, j=fifo_stack.length; i<j; i++) {
			var batch = fifo_stack.pop();
			if(batch[0] >= qty) {
				batch[0] = batch[0] - qty;
				fifo_value_diff += (qty * batch[1]);
				
				qty = 0.0;
				if(batch[0]) {
					// batch still has qty put it back
					fifo_stack.push(batch);
				}
				
				// all qty found
				break;
			} else {
				// consume this batch fully
				fifo_value_diff += (batch[0] * batch[1]);
				qty = qty - batch[0];
			}
		}
		if(qty) {
			// msgprint("Negative values not allowed for FIFO valuation!\
			// Item " + sl.item_code.bold() + " on " + dateutil.str_to_user(sl.posting_datetime).bold() +
			// " becomes negative. Values computed will not be accurate.");
		}
		
		// reset the updated stack
		wh.fifo_stack = fifo_stack.reverse();
		return -fifo_value_diff;
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
	get_plot_points: function(item, col, idx) {
		return [[dateutil.user_to_obj(col.name).getTime(), item[col.field]]]
	}
});