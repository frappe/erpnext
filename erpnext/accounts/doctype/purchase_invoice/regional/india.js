{% include "erpnext/regional/india/taxes.js" %}

erpnext.setup_auto_gst_taxation('Purchase Invoice');


frappe.ui.form.on('Purchase Taxes and Charges', {
	taxes_add: function(frm) {
		if (frm.doc.reverse_charge === 'Y') {
			frappe.call({
				'method': 'erpnext.regional.india.utils.get_gst_accounts',
				'args': {
					company: frm.doc.company
				},
				'callback': function(r) {
					let accounts = r.message;
					let account_list = accounts['cgst_account'] + accounts['sgst_account']
						+ accounts['igst_account']

					let gst_tax = 0;

					$.each(frm.doc.taxes || [], function(i, row) {
						if (account_list.includes(row.account_head)) {
							gst_tax += row.base_tax_amount_after_discount_amount;
						}
					});

					frm.doc.taxes_and_charges_added -= flt(gst_tax);
					frm.refresh_field('taxes_and_charges_added');
				}
			})
		}
	}
});
