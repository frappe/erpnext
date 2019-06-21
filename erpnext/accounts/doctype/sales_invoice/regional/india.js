frappe.ui.form.on("Sales Invoice", {
	setup: function(frm) {
		frm.set_query('transporter', function() {
			return {
				filters: {
					'is_transporter': 1
				}
			};
		});

		frm.set_query('driver', function(doc) {
			return {
				filters: {
					'transporter': doc.transporter
				}
			};
		});
	},

	refresh: function(frm) {
		if(frm.doc.docstatus == 1 && !frm.is_dirty()
			&& !frm.doc.is_return && !frm.doc.ewaybill) {

			frm.add_custom_button('e-Way Bill JSON', () => {
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
			}, __("Make"));
		}
	}
});
