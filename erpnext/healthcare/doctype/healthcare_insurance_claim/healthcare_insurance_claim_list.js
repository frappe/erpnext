frappe.listview_settings['Healthcare Insurance Claim'] = {
	add_fields: ['name', 'status'],
	filters: [['docstatus', '=', '1']],
	get_indicator: function(doc) {
		return [__(doc.status), {
			'Invoiced': 'orange',
			'Paid': 'green',
			'Resubmitted': 'light-blue',
			'Submitted': 'blue'
		}[doc.status], 'status,=,' + doc.status];
	}
};