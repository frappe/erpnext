// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/selling/sales_common.js' %};

erpnext.selling.POSInvoiceController = erpnext.selling.SellingController.extend({
	setup(doc) {
		this.setup_posting_date_time_check();
		this._super(doc);
	},

	onload(doc) {
		this._super(doc);
	},

	calculate_taxes_and_totals() {
		this._calculate_taxes_and_totals();
		this.calculate_discount_amount();
	},

	is_pos: function(frm){
		this.set_pos_data();
	},

	set_pos_data: function() {
		if(this.frm.doc.is_pos) {
			this.frm.set_value("allocate_advances_automatically", 0);
			if(!this.frm.doc.company) {
				this.frm.set_value("is_pos", 0);
				frappe.msgprint(__("Please specify Company to proceed"));
			} else {
				var me = this;
				return this.frm.call({
					doc: me.frm.doc,
					method: "set_missing_values",
					callback: function(r) {
						if(!r.exc) {
							if(r.message && r.message.print_format) {
								me.frm.pos_print_format = r.message.print_format;
							}
							me.frm.script_manager.trigger("update_stock");
							if(me.frm.doc.taxes_and_charges) {
								me.frm.script_manager.trigger("taxes_and_charges");
							}
							frappe.model.set_default_values(me.frm.doc);
							me.set_dynamic_labels();
							me.calculate_taxes_and_totals();
						}
					}
				});
			}
		}
		else this.frm.trigger("refresh");
	},

	customer() {
		if (!this.frm.doc.customer) return

		if (this.frm.doc.is_pos){
			var pos_profile = this.frm.doc.pos_profile;
		}
		var me = this;
		if(this.frm.updating_party_details) return;
		erpnext.utils.get_party_details(this.frm,
			"erpnext.accounts.party.get_party_details", {
				posting_date: this.frm.doc.posting_date,
				party: this.frm.doc.customer,
				party_type: "Customer",
				account: this.frm.doc.debit_to,
				price_list: this.frm.doc.selling_price_list,
				pos_profile: pos_profile
			}, function() {
				me.apply_pricing_rule();
			});

		// if(this.frm.doc.customer) {
		// 	frappe.call({
		// 		"method": "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_loyalty_programs",
		// 		"args": {
		// 			"customer": this.frm.doc.customer
		// 		},
		// 		callback: function(r) {
		// 			if(r.message && r.message.length) {
		// 				select_loyalty_program(me.frm, r.message);
		// 			}
		// 		}
		// 	});
		// }
	},
})

$.extend(cur_frm.cscript, new erpnext.selling.POSInvoiceController({ frm: cur_frm }))

frappe.ui.form.on('POS Invoice', {
	
});
