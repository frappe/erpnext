wn.pages['general-ledger'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: 'General Ledger',
		single_column: true
	});
	
	erpnext.general_ledger = new wn.views.GridReport({
		parent: $(wrapper).find('.layout-main'),
		appframe: wrapper.appframe,
		doctypes: ["Company", "Account", "GL Entry"],
		filters: [
			{fieldtype:"Select", label: "Company", options:"Company",
				filter: function(val, item) {
					return item.company == val || val == "Select Company";
				}},
			{fieldtype:"Select", label: "Account", options:"Account",
				filter: function(val, item) {
					return item.account == val || val == "Select Account";
				}},
			{fieldtype:"Date", label: "From Date"},
			{fieldtype:"Label", label: "To"},
			{fieldtype:"Date", label: "To Date"},
			{fieldtype:"Button", label: "Refresh"},
		],
		setup: function() {
			this.setup_filters();
			this.setup_columns();
		},
		setup_filters: function() {
			var me = this;
			// default filters
			this.filter_inputs.company.val(sys_defaults.company);
			this.filter_inputs.from_date.val(dateutil.str_to_user(sys_defaults.year_start_date));
			this.filter_inputs.to_date.val(dateutil.str_to_user(sys_defaults.year_end_date));
			this.filter_inputs.refresh.click(function() { me.refresh(); })
		},
		setup_columns: function() {
			this.columns = [
				{id: "posting_date", name: "Posting Date", field: "posting_date", width: 100,
					formatter: this.date_formatter},
				{id: "account", name: "Account", field: "account", width: 240},
				{id: "debit", name: "Debit", field: "debit", width: 100,
					formatter: this.currency_formatter},
				{id: "credit", name: "Credit", field: "credit", width: 100,
					formatter: this.currency_formatter},
			];
		},
		prepare_data: function() {
			this.prepare_data_view(wn.report_dump.data["GL Entry"]);
		},
		dataview_filter: function(item) {
			var filters = wn.cur_grid_report.filter_inputs;
			for (i in filters) {
				var filter = filters[i].get(0);
				if(filter.opts.filter && !filter.opts.filter($(filter).val(), item)) {
					return false;
				}
			}
			return true;
		},
	});
	
}

