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
					return item.company == val || val == opts.default_value;
				}},
			{fieldtype:"Select", label: "Account", options:"Account", default_value: "Select Account...",
				filter: function(val, item, opts) {
					return item.account == val || val == opts.default_value;
				}},
			{fieldtype:"Data", label: "Voucher No",
				filter: function(val, item, opts) {
					if(!val) return true;
					return item.voucher_no.indexOf(val)!=-1;
				}},
			{fieldtype:"Date", label: "From Date", filter: function(val, item) {
				return dateutil.user_to_obj(val) <= dateutil.str_to_obj(item.posting_date);
			}},
			{fieldtype:"Label", label: "To"},
			{fieldtype:"Date", label: "To Date", filter: function(val, item) {
				return dateutil.user_to_obj(val) >= dateutil.str_to_obj(item.posting_date);
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
			this.prepare_data_view(wn.report_dump.data["GL Entry"]);
		},
	});

}

