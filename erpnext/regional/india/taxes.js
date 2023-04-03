erpnext.setup_auto_gst_taxation = (doctype) => {
	frappe.ui.form.on(doctype, {
		company_address: function(frm) {
			frm.trigger('get_tax_template');
		},
		shipping_address: function(frm) {
			frm.trigger('get_tax_template');
		},
		supplier_address: function(frm) {
			frm.trigger('get_tax_template');
		},
		tax_category: function(frm) {
			frm.trigger('get_tax_template');
		},
		customer_address: function(frm) {
			frm.trigger('get_tax_template');
		},
		get_tax_template: function(frm) {
			if (!frm.doc.company) return;

			let party_details = {
				'shipping_address': frm.doc.shipping_address || '',
				'shipping_address_name': frm.doc.shipping_address_name || '',
				'customer_address': frm.doc.customer_address || '',
				'company_address': frm.doc.company_address,
				'supplier_address': frm.doc.supplier_address,
				'customer': frm.doc.customer,
				'supplier': frm.doc.supplier,
				'supplier_gstin': frm.doc.supplier_gstin,
				'company_gstin': frm.doc.company_gstin,
				'tax_category': frm.doc.tax_category
			};

			frappe.call({
				method: 'erpnext.regional.india.utils.get_regional_address_details',
				args: {
					party_details: JSON.stringify(party_details),
					doctype: frm.doc.doctype,
					company: frm.doc.company
				},
				debounce: 2000,
				callback: function(r) {
					if(r.message) {
						frm.set_value('taxes_and_charges', r.message.taxes_and_charges);
						frm.set_value('taxes', r.message.taxes);
						frm.set_value('place_of_supply', r.message.place_of_supply);
					}
				}
			});
		},

		reverse_charge: function(frm) {
			if (frm.doc.reverse_charge == "Y") {
				frm.set_value('eligibility_for_itc', 'ITC on Reverse Charge');
			}
		}
	});
}
