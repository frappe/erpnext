// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Healthcare Insurance Payment Request', {
	refresh: function(frm) {
		frm.set_query('insurance_company', function() {
			return {
				filters: {
					'company': frm.doc.company
				}
			};
		});

		if (frm.doc.docstatus == 1) {
			frm.add_custom_button(__('Payment'), function() {
				frm.trigger('make_payment_entry');
			});
		}
	},

	from_date: function(frm) {
		frm.trigger('get_insurance_claims');
	},

	to_date: function(frm) {
		frm.trigger('get_insurance_claims');
	},

	insurance_company: function(frm) {
		frm.trigger('get_insurance_claims');
	},

	posting_date_type: function(frm) {
		frm.trigger('get_insurance_claims');
	},

	get_insurance_claims: function(frm) {
		frm.doc.claims = [];

		frappe.call({
			method: 'set_claim_items',
			doc: frm.doc,
			freeze: true,
			freeze_message: __('Fetching Claims'),
			callback: function() {
				refresh_field('claims');
				frm.trigger('set_total_claim_amount');
			}
		});
	},

	set_total_claim_amount: function(frm) {
		let total_claim_amount = 0.0;

		$.each(frm.doc.claims || [], (_i, claim) => {
			total_claim_amount += flt(claim.claim_amount);
		});

		frm.set_value('total_claim_amount', total_claim_amount);
		refresh_field('total_claim_amount');
	},

	make_payment_entry: function(frm) {
		return frappe.call({
			method: 'erpnext.healthcare.doctype.healthcare_insurance_payment_request.healthcare_insurance_payment_request.create_payment_entry',
			args: {'doc': frm.doc},
			callback: function(r) {
				let doc = frappe.model.sync(r.message);
				frappe.set_route('Form', doc[0].doctype, doc[0].name);
			}
		});
	}
});
