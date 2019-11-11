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

	onload: function(frm) {
		frm.trigger('get_gst_accounts');
	},

	company: function(frm) {
		frm.trigger('get_gst_accounts');
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
	},

	place_of_supply: function(frm) {
		frm.trigger('set_accounts_to_skip');
	},

	get_gst_accounts: function(frm) {
		frappe.call({
			method: "erpnext.regional.india.utils.get_gst_accounts",
			args : {
				company: frm.doc.company
			},
			callback: function(r) {
				frm.doc.gst_accounts = r.message;
			}
		});
	},

	set_accounts_to_skip: function(frm) {

		let intra_state_gst_accounts = frm.doc.gst_accounts['cgst_account'].concat(frm.doc.gst_accounts['sgst_account']);
		let inter_state_gst_accounts = frm.doc.gst_accounts['igst_account'];

		if (frm.doc.gst_category == 'SEZ' && frm.doc.export_type == 'Without Payment of Tax') {
			frm.doc.accounts_to_skip = JSON.stringify(intra_state_gst_accounts.concat(inter_state_gst_accounts));
			return;
		} else if (frm.doc.gst_category == 'SEZ' && frm.doc.export_type == 'With Payment of Tax') {
			frm.doc.accounts_to_skip = JSON.stringify(intra_state_gst_accounts);
			return;
		}

		if (!frm.doc.place_of_supply || (!frm.doc.company_gstin)) {
			return;
		}

		if (frm.doc.company_gstin
			&& (frm.doc.place_of_supply.substring(0, 2) != frm.doc.company_gstin.substring(0, 2))) {
			frm.doc.accounts_to_skip = JSON.stringify(intra_state_gst_accounts);
		} else {
			frm.doc.accounts_to_skip = JSON.stringify(inter_state_gst_accounts);
		}

	}
});

frappe.ui.form.on("Sales Invoice Item", {
	item_code: function(frm) {
		if (!frm.doc.gst_accounts) {
			frappe.run_serially([
				() => frm.trigger('get_gst_accounts'),
				() => frm.trigger('set_accounts_to_skip')
			]);
		}
	}
});
