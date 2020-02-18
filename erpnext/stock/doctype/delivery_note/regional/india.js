{% include "erpnext/regional/india/taxes.js" %}

erpnext.setup_auto_gst_taxation('Delivery Note');

frappe.ui.form.on('Delivery Note', {
    refresh: function(frm) {
        if(frm.doc.docstatus == 1 && !frm.is_dirty() && !frm.doc.ewaybill) {
			frm.add_custom_button('E-Way Bill JSON', () => {
				var w = window.open(
					frappe.urllib.get_full_url(
						"/api/method/erpnext.regional.india.utils.generate_ewb_json?"
						+ "dt=" + encodeURIComponent(frm.doc.doctype)
						+ "&dn=" + encodeURIComponent(frm.doc.name)
					)
				);
				if (!w) {
					frappe.msgprint(__("Please enable pop-ups")); return;
				}
			}, __("Create"));
		}
    }
})

