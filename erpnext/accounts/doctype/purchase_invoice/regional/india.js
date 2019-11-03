frappe.ui.form.on("Purchase Invoice", {
	onload: function(frm) {
		frm.trigger('get_gst_accounts');
	},

	company: function(frm) {
		frm.trigger('get_gst_accounts');
	},

	place_of_supply: function(frm) {
		frm.trigger('set_accounts_to_skip');
	},

	supplier_gstin: function(frm) {
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

		if (! frm.doc.place_of_supply) {
			return;
		}

		let intra_state_gst_accounts = frm.doc.gst_accounts['cgst_account'].concat(frm.doc.gst_accounts['sgst_account']);
		let inter_state_gst_accounts = frm.doc.gst_accounts['igst_account'];

		if (frm.doc.supplier_gstin
			&& (frm.doc.place_of_supply.substring(0, 2) != frm.doc.supplier_gstin.substring(0, 2))) {
			frm.doc.accounts_to_skip = JSON.stringify(intra_state_gst_accounts);
		} else {
			frm.doc.accounts_to_skip = JSON.stringify(inter_state_gst_accounts);
		}
	}
});

frappe.ui.form.on("Purchase Invoice Item", {
	item_code: function(frm) {
		if (!frm.doc.gst_accounts) {
			frappe.run_serially([
				() => frm.trigger('get_gst_accounts'),
				() => frm.trigger('set_accounts_to_skip')
			]);
		}
	}
});
