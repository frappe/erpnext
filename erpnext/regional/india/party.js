erpnext.setup_gst_reminder_button = (doctype) => {
	frappe.ui.form.on(doctype, {
		refresh: (frm) => {
			if(!frm.is_new()) {
				var missing = false;
				frm.doc.__onload.addr_list && frm.doc.__onload.addr_list.forEach((d) => {
					if(!d.gstin) missing = true;
				});
				if (!missing) return;

				frm.add_custom_button('Send GST Update Reminder', () => {
					return new Promise((resolve) => {
						return frappe.call({
							method: 'erpnext.regional.doctype.gst_settings.gst_settings.send_gstin_reminder',
							args: {
								party_type: frm.doc.doctype,
								party: frm.doc.name,
							}
						}).always(() => { resolve(); });
					});
				});
			}
		}
	});
};
