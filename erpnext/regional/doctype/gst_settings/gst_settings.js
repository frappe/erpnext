// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('GST Settings', {
	refresh: function(frm) {
		frm.add_custom_button('Send GST Update Reminder', () => {
			return new Promise((resolve) => {
				return frappe.call({
					method: 'erpnext.regional.doctype.gst_settings.gst_settings.send_reminder'
				}).always(() => { resolve(); });
			});
		});

		$(frm.fields_dict.gst_summary.wrapper).empty().html(
			`<table class="table table-bordered">
				<tbody>
				<tr>
				<td>Total Addresses</td><td>${frm.doc.__onload.data.total_addresses}</td>
				</tr><tr>
				<td>Total Addresses with GST</td><td>${frm.doc.__onload.data.total_addresses_with_gstin}</td>
				</tr>
			</tbody></table>`
		);
	}
});
