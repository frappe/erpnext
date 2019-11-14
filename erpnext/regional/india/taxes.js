erpnext.setup_auto_gst_taxation = (doctype) => {
	frappe.ui.form.on(doctype, {
		onload: function(frm) {
			frm.trigger('get_gst_accounts');
		},

		customer_address: function(frm) {
			frm.trigger('set_accounts_to_skip');
		},

		shipping_address_name: function(frm) {
			frm.trigger('set_accounts_to_skip');
		},

		supplier_address: function(frm) {
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
			if(!frm.doc.taxes_and_charges){
				return;
			}

			let intra_state_gst_accounts = frm.doc.gst_accounts['cgst_account'].concat(frm.doc.gst_accounts['sgst_account']);
			let inter_state_gst_accounts = frm.doc.gst_accounts['igst_account'];

			let accounts = intra_state_gst_accounts.concat(inter_state_gst_accounts);
			let account_heads = [];
			let accounts_to_skip =[];

			frm.call({
				method: "erpnext.controllers.accounts_controller.get_taxes_and_charges",
				args: {
					master_doctype: "Sales Taxes and Charges Template",
					master_name: frm.doc.taxes_and_charges
				},
				callback: function(r) {
					frm.doc.taxes.forEach((tax) => {
						account_heads.push(tax.account_head);
					});

					accounts.forEach((account) => {
						if(!in_list(account_heads, account)) {
							accounts_to_skip.push(account);
						}
					});

					frm.doc.accounts_to_skip = JSON.stringify(accounts_to_skip);
				}
			});
		}
	});

	frappe.ui.form.on(doctype +' Item', {
		item_code: function(frm) {
			console.log("Test");
			frappe.run_serially([
				() => {
					if(!frm.doc.gst_accounts) {
						frm.trigger('get_gst_accounts');
					}
				},
				() => {
					if(!frm.doc.accounts_to_skip) {
						frm.trigger('set_accounts_to_skip');
					}
				}
			]);
		}
	});
}

