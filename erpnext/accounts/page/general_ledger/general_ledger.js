wn.pages['general-ledger'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: 'General Ledger',
		single_column: true
	});
	
	erpnext.general_ledger = new wn.views.GridReport({
		title: "General Ledger",
		parent: $(wrapper).find('.layout-main'),
		appframe: wrapper.appframe,
		doctypes: ["Company", "Account", "GL Entry"],
		setup: function() {
			this.setup_filters();
			this.setup_columns();
		},
		setup_columns: function() {
			this.columns = [
				{id: "posting_date", name: "Posting Date", field: "posting_date", width: 100,
					formatter: this.date_formatter},
				{id: "account", name: "Account", field: "account", width: 240, 	
					link_formatter: {
						filter_input: "account",
						open_btn: true,
						doctype: '"Account"'
					}},
				{id: "debit", name: "Debit", field: "debit", width: 100,
					formatter: this.currency_formatter},
				{id: "credit", name: "Credit", field: "credit", width: 100,
					formatter: this.currency_formatter},
				{id: "voucher_type", name: "Voucher Type", field: "voucher_type", width: 120},
				{id: "voucher_no", name: "Voucher No", field: "voucher_no", width: 160,
					link_formatter: {
						filter_input: "voucher_no",
						open_btn: true,
						doctype: "dataContext.voucher_type"
					}},
				{id: "remarks", name: "Remarks", field: "remarks", width: 200,
					formatter: this.text_formatter},
					
			];
		},
		filters: [
			{fieldtype:"Select", label: "Company", options:"Company", default_value: "Select Company...",
				filter: function(val, item, opts) {
					return item.company == val || val == opts.default_value || item._show;
				}},
			{fieldtype:"Select", label: "Account", options:"Account", default_value: "Select Account...",
				filter: function(val, item, opts) {
					return item.account == val || val == opts.default_value || item._show;
				}},
			{fieldtype:"Data", label: "Voucher No",
				filter: function(val, item, opts) {
					if(!val) return true;
					return (item.voucher_no && item.voucher_no.indexOf(val)!=-1) || item._show;
				}},
			{fieldtype:"Date", label: "From Date", filter: function(val, item) {
				return item._show || dateutil.user_to_obj(val) <= dateutil.str_to_obj(item.posting_date);
			}},
			{fieldtype:"Label", label: "To"},
			{fieldtype:"Date", label: "To Date", filter: function(val, item) {
				return item._show || dateutil.user_to_obj(val) >= dateutil.str_to_obj(item.posting_date);
			}},
			{fieldtype:"Button", label: "Refresh", icon:"icon-refresh icon-white", cssClass:"btn-info"},
			{fieldtype:"Button", label: "Reset Filters"}
		],
		setup_filters: function() {
			var me = this;
			// default filters
			this.init_filter_values();
			this.filter_inputs.refresh.click(function() { me.set_route(); })
			this.filter_inputs.reset_filters.click(function() { me.init_filter_values(); me.set_route(); })
		},
		init_filter_values: function() {
			this.filter_inputs.company.val(sys_defaults.company);
			this.filter_inputs.from_date.val(dateutil.str_to_user(sys_defaults.year_start_date));
			this.filter_inputs.to_date.val(dateutil.str_to_user(sys_defaults.year_end_date));
			this.filter_inputs.voucher_no.val("");
			this.filter_inputs.account.get(0).selectedIndex = 0;			
		},
		prepare_data: function() {
			// add Opening, Closing, Totals rows
			// if filtered by account and / or voucher
			var data = wn.report_dump.data["GL Entry"];
			
			var account = this.filter_inputs.account.val();
			var from_date = dateutil.user_to_obj(this.filter_inputs.from_date.val());
			var to_date = dateutil.user_to_obj(this.filter_inputs.to_date.val());
			var voucher_no = this.filter_inputs.voucher_no.val();
			var default_account = this.filter_inputs.account.get(0).opts.default_value;
			
			if(to_date < from_date) {
				msgprint("From Date must be before To Date");
				return;
			}
			
			var opening = {
				account: "Opening", debit: 0.0, credit: 0.0, 
					id:"_opening", _show: true, _style: "font-weight: bold"
			}
			var totals = {
				account: "Totals", debit: 0.0, credit: 0.0, 
					id:"_totals", _show: true, _style: "font-weight: bold"
			}
			
			$.each(data, function(i, item) {
				if((account!=default_account ? item.account==account : true) && 
					(voucher_no ? item.voucher_no==voucher_no : true)) {
					var date = dateutil.str_to_obj(item.posting_date);
					if(date < from_date) {
						opening.debit += item.debit;
						opening.credit += item.credit;
					} else if(date <= to_date) {
						totals.debit += item.debit;
						totals.credit += item.credit;						
					}
				}
			})

			var closing = {
				account: "Closing (Opening + Totals)", debit: opening.debit + totals.debit, 
					credit: opening.credit + totals.credit, 
					id:"_closing", _show: true, _style: "font-weight: bold"
			}
								
			
			if(account != default_account) {
				var out = [opening].concat(data).concat([totals, closing]);
			} else {
				var out = data.concat([totals]);
			}
			
			this.prepare_data_view(out);
		},
	});

}

