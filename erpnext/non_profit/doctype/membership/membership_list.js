frappe.listview_settings['Membership'] = {
	get_indicator: function(doc) {
		if (doc.membership_status == 'New') {
			return [__('New'), 'blue', 'membership_status,=,New'];
		} else if (doc.membership_status === 'Current') {
			return [__('Current'), 'green', 'membership_status,=,Current'];
		} else if (doc.membership_status === 'Pending') {
			return [__('Pending'), 'yellow', 'membership_status,=,Pending'];
		} else if (doc.membership_status === 'Expired') {
			return [__('Expired'), 'grey', 'membership_status,=,Expired'];
		} else {
			return [__('Cancelled'), 'red', 'membership_status,=,Cancelled'];
		}
	}
};
