wn.pages['stock-ledger'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: 'Stock Ledger',
		single_column: true
	});
	
	erpnext.stock_ledger = new wn.views.GridReport({
		title: "Stock Ledger",
		page: wrapper,
		parent: $(wrapper).find('.layout-main'),
		appframe: wrapper.appframe,
		doctypes: ["Item", "Item Group", "Warehouse", "Stock Ledger Entry"],

		setup_columns: function() {
			this.columns = [
				{id: "posting_datetime", name: "Posting Date", field: "posting_datetime", width: 120,
					formatter: this.date_formatter},
				{id: "item_code", name: "Item Code", field: "item_code", width: 160, 	
					link_formatter: {
						filter_input: "item_code",
						open_btn: true,
						doctype: '"Item"'
					}},
				{id: "warehouse", name: "Warehouse", field: "warehouse", width: 100,
					link_formatter: {filter_input: "warehouse"}},
				{id: "qty", name: "Qty", field: "qty", width: 100,
					formatter: this.currency_formatter},
				{id: "balance", name: "Balance", field: "balance", width: 100,
					formatter: this.currency_formatter},
				{id: "voucher_type", name: "Voucher Type", field: "voucher_type", width: 120},
				{id: "voucher_no", name: "Voucher No", field: "voucher_no", width: 160,
					link_formatter: {
						filter_input: "voucher_no",
						open_btn: true,
						doctype: "dataContext.voucher_type"
					}},
				{id: "description", name: "Description", field: "description", width: 200,
					formatter: this.text_formatter},
			];
		},
		filters: [
			{fieldtype:"Select", label: "Warehouse", link:"Warehouse", default_value: "Select Warehouse...",
				filter: function(val, item, opts) {
					return item.warehouse == val || val == opts.default_value;
				}},
			{fieldtype:"Select", label: "Item Code", link:"Item", default_value: "Select Item...",
				filter: function(val, item, opts) {
					return item.item_code == val || val == opts.default_value;
				}},
			{fieldtype:"Data", label: "Voucher No",
				filter: function(val, item, opts) {
					if(!val) return true;
					return (item.voucher_no && item.voucher_no.indexOf(val)!=-1);
				}},
			{fieldtype:"Date", label: "From Date", filter: function(val, item) {
				return dateutil.str_to_obj(val) <= dateutil.str_to_obj(item.posting_date);
			}},
			{fieldtype:"Label", label: "To"},
			{fieldtype:"Date", label: "To Date", filter: function(val, item) {
				return dateutil.str_to_obj(val) >= dateutil.str_to_obj(item.posting_date);
			}},
			{fieldtype:"Button", label: "Refresh", icon:"icon-refresh icon-white", cssClass:"btn-info"},
			{fieldtype:"Button", label: "Reset Filters"}
		],
		init_filter_values: function() {
			this.filter_inputs.warehouse.get(0).selectedIndex = 0;
			this.filter_inputs.item_code.get(0).selectedIndex = 0;			
			this.filter_inputs.from_date.val(dateutil.str_to_user(sys_defaults.year_start_date));
			this.filter_inputs.to_date.val(dateutil.str_to_user(sys_defaults.year_end_date));
			this.filter_inputs.voucher_no.val("");
		},
		prepare_data: function() {
			var me = this;
			if(!this.item_by_name)
				this.item_by_name = this.make_name_map(wn.report_dump.data["Item"]);
			var data = wn.report_dump.data["Stock Ledger Entry"];
			var out = [];
			
			if(this.to_date < this.from_date) {
				msgprint("From Date must be before To Date");
				return;
			}

			var opening = {
				item_code: "On " + dateutil.str_to_user(this.from_date), qty: 0.0, balance: 0.0,
					id:"_opening", _show: true, _style: "font-weight: bold"
			}
			var total_in = {
				item_code: "Total In", qty: 0.0, balance: 0.0,
					id:"_total_in", _show: true, _style: "font-weight: bold"
			}
			var total_out = {
				item_code: "Total Out", qty: 0.0, balance: 0.0,
					id:"_total_out", _show: true, _style: "font-weight: bold"
			}
			
			// clear balance
			$.each(wn.report_dump.data["Item"], function(i, item) { item.balance = 0.0; });
			
			// 
			var t = new Date();
			for(var i=0, j=data.length; i<j; i++) {
				var sl = data[i];
				sl.description = me.item_by_name[sl.item_code].description;
				sl.posting_datetime = sl.posting_date + " " + sl.posting_time;
				var posting_datetime = dateutil.str_to_obj(sl.posting_datetime);
				
				// opening, transactions, closing, total in, total out
				var before_end = posting_datetime <= dateutil.str_to_obj(me.to_date + " 23:59:59");
				if((!me.is_default("item_code") ? me.apply_filter(sl, "item_code") : true)
					&& me.apply_filter(sl, "warehouse") && me.apply_filter(sl, "voucher_no")) {
					if(posting_datetime < dateutil.str_to_obj(me.from_date)) {
						opening.balance += sl.qty;
					} else if(before_end) {
						if(sl.qty > 0) total_in.qty += sl.qty;
						else total_out.qty += (-1 * sl.qty);
					}
				}
				
				if(!before_end) break;
				
				// apply filters
				if(me.dataview_filter(sl)) {
					out.push(sl);
				}
				
				// update balance
				if((!me.is_default("warehouse") ? me.apply_filter(sl, "warehouse") : true)) {
					sl.balance = me.item_by_name[sl.item_code].balance + sl.qty;
					me.item_by_name[sl.item_code].balance = sl.balance;					
				}
			}
			
			console.log(new Date() - t);
			
			if(me.item_code != me.item_code_default && !me.voucher_no) {
				var closing = {
					item_code: "On " + dateutil.str_to_user(this.to_date), 
					balane: me.item_by_name[sl.item_code].balance, qty: 0,
					id:"_closing", _show: true, _style: "font-weight: bold"
				};
				var out = [opening].concat(out).concat([total_in, total_out, closing]);
			}
			
			this.data = out;
			this.prepare_data_view(out);			
		},
	});
}