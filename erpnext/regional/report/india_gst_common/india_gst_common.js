function fetch_gstins(report) {
	var company_gstins = report.get_filter('company_gstin');
	var company = report.get_filter_value('company');
	if (company) {
		frappe.call({
			method:'erpnext.regional.india.utils.get_gstins_for_company',
			async: false,
			args: {
				company: company
			},
			callback: function(r) {
				r.message.unshift("");
				company_gstins.df.options = r.message;
				company_gstins.refresh();
			}
		});
	} else {
		company_gstins.df.options = [""];
		company_gstins.refresh();
	}
}