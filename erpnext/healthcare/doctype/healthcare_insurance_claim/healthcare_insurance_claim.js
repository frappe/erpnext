// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Healthcare Insurance Claim', {
	refresh: function(frm) {
		frm.ignore_doctypes_on_cancel_all = [frm.doc.service_doctype];

		frm.set_query('healthcare_insurance_coverage_plan', function() {
			return {
				filters: {
					'is_active': 1
				}
			};
		});

		frm.set_query('insurance_subscription', function() {
			return {
				filters: {
					'patient': frm.doc.patient,
					'docstatus': 1
				}
			};
		});

		frm.set_query('healthcare_service_type', function() {
			let service_doctypes = ['Medication', 'Therapy Type', 'Lab Test Template',
				'Clinical Procedure Template'];
			return {
				filters: {
					name: ['in', service_doctypes]
				}
			};
		});

		frm.set_query('patient', function() {
			return {
				filters: {
					'status': 'Active'
				}
			};
		});

		if (frm.doc.docstatus===1) {
			frm.add_custom_button(__('Create Coverage'), () => {
				frappe.call({
					method: 'erpnext.healthcare.doctype.healthcare_insurance_claim.healthcare_insurance_claim.create_insurance_coverage',
					args: { doc: frm.doc },
					freeze: true,
					callback: function(r) {
						var doclist = frappe.model.sync(r.message);
						frappe.set_route('Form', doclist[0].doctype, doclist[0].name);
					}
				});
			});

			frm.add_custom_button(__(frm.doc.service_doctype), () => {
				frappe.db.get_value(frm.doc.service_doctype, {'insurance_claim': frm.doc.name}, 'name', (r) => {
					if (r && r.name) {
						frappe.set_route('Form', frm.doc.service_doctype, r.name);
					}
				});
			}, __('View'));
		}
	},

	price_list_rate: function(frm) {
		if (frm.doc.price_list_rate) {
			frm.trigger('calculate_claim_amount_on_update');
		}
	},

	discount: function(frm) {
		if (frm.doc.discount) {
			frm.trigger('calculate_claim_amount_on_update');
		}
	},

	coverage: function(frm) {
		if (frm.doc.coverage) {
			frm.trigger('calculate_claim_amount_on_update');
		}
	},

	calculate_claim_amount_on_update: function(frm) {
		if (frm.doc.price_list_rate) {
			let discount_amount = 0.0;
			let rate = frm.doc.price_list_rate;

			if (frm.doc.discount) {
				discount_amount = flt(frm.doc.price_list_rate) * flt(frm.doc.discount) * 0.01;
				rate = flt(rate) - flt(discount_amount)
			}

			let amount = flt(frm.doc.quantity) * flt(rate);
			frm.set_value('amount', amount);
		}

		if (frm.doc.amount && frm.doc.coverage) {
			let coverage_amount = flt(frm.doc.amount) * 0.01 * flt(frm.doc.coverage);
			frm.set_value('coverage_amount', coverage_amount);
		}
	}
});
