// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/selling/sales_common.js' %};

erpnext.selling.POSInvoiceController = erpnext.selling.SellingController.extend({
	setup(doc) {
		this.setup_posting_date_time_check();
		this._super(doc);
	},

	onload() {
		this._super();
		if(this.frm.doc.__islocal && this.frm.doc.is_pos) {
			//Load pos profile data on the invoice if the default value of Is POS is 1

			me.frm.script_manager.trigger("is_pos");
			me.frm.refresh_fields();
		}
	},

	refresh(doc) {
		this._super();
		if (doc.docstatus == 1 && !doc.is_return) {
			if(doc.outstanding_amount >= 0 || Math.abs(flt(doc.outstanding_amount)) < flt(doc.grand_total)) {
				cur_frm.add_custom_button(__('Return'),
					this.make_sales_return, __('Create'));
				cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
			}
		}

		if (this.frm.doc.is_return) {
			this.frm.return_print_format = "Sales Invoice Return";
			cur_frm.set_value('consolidated_invoice', '');
		}
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
							if(r.message) {
								me.frm.pos_print_format = r.message.print_format || "";
								me.frm.meta.default_print_format = r.message.print_format || "";
								me.frm.allow_edit_rate = r.message.allow_edit_rate;
								me.frm.allow_edit_discount = r.message.allow_edit_discount;
								me.frm.doc.campaign = r.message.campaign;
								me.frm.allow_print_before_pay = r.message.allow_print_before_pay;
							}
							me.frm.script_manager.trigger("update_stock");
							me.calculate_taxes_and_totals();
							if(me.frm.doc.taxes_and_charges) {
								me.frm.script_manager.trigger("taxes_and_charges");
							}
							frappe.model.set_default_values(me.frm.doc);
							me.set_dynamic_labels();
							
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
	},

	amount: function(){
		this.write_off_outstanding_amount_automatically()
	},

	change_amount: function(){
		if(this.frm.doc.paid_amount > this.frm.doc.grand_total){
			this.calculate_write_off_amount();
		}else {
			this.frm.set_value("change_amount", 0.0);
			this.frm.set_value("base_change_amount", 0.0);
		}

		this.frm.refresh_fields();
	},

	loyalty_amount: function(){
		this.calculate_outstanding_amount();
		this.frm.refresh_field("outstanding_amount");
		this.frm.refresh_field("paid_amount");
		this.frm.refresh_field("base_paid_amount");
	},

	write_off_outstanding_amount_automatically: function() {
		if(cint(this.frm.doc.write_off_outstanding_amount_automatically)) {
			frappe.model.round_floats_in(this.frm.doc, ["grand_total", "paid_amount"]);
			// this will make outstanding amount 0
			this.frm.set_value("write_off_amount",
				flt(this.frm.doc.grand_total - this.frm.doc.paid_amount - this.frm.doc.total_advance, precision("write_off_amount"))
			);
			this.frm.toggle_enable("write_off_amount", false);

		} else {
			this.frm.toggle_enable("write_off_amount", true);
		}

		this.calculate_outstanding_amount(false);
		this.frm.refresh_fields();
	},

	make_sales_return: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.pos_invoice.pos_invoice.make_sales_return",
			frm: cur_frm
		})
	},
})

$.extend(cur_frm.cscript, new erpnext.selling.POSInvoiceController({ frm: cur_frm }))

frappe.ui.form.on('POS Invoice', {
	redeem_loyalty_points: function(frm) {
		frm.events.get_loyalty_details(frm);
	},

	loyalty_points: function(frm) {
		if (frm.redemption_conversion_factor) {
			frm.events.set_loyalty_points(frm);
		} else {
			frappe.call({
				method: "erpnext.accounts.doctype.loyalty_program.loyalty_program.get_redeemption_factor",
				args: {
					"loyalty_program": frm.doc.loyalty_program
				},
				callback: function(r) {
					if (r) {
						frm.redemption_conversion_factor = r.message;
						frm.events.set_loyalty_points(frm);
					}
				}
			});
		}
	},

	get_loyalty_details: function(frm) {
		if (frm.doc.customer && frm.doc.redeem_loyalty_points) {
			frappe.call({
				method: "erpnext.accounts.doctype.loyalty_program.loyalty_program.get_loyalty_program_details",
				args: {
					"customer": frm.doc.customer,
					"loyalty_program": frm.doc.loyalty_program,
					"expiry_date": frm.doc.posting_date,
					"company": frm.doc.company
				},
				callback: function(r) {
					if (r) {
						frm.set_value("loyalty_redemption_account", r.message.expense_account);
						frm.set_value("loyalty_redemption_cost_center", r.message.cost_center);
						frm.redemption_conversion_factor = r.message.conversion_factor;
					}
				}
			});
		}
	},

	set_loyalty_points: function(frm) {
		if (frm.redemption_conversion_factor) {
			let loyalty_amount = flt(frm.redemption_conversion_factor*flt(frm.doc.loyalty_points), precision("loyalty_amount"));
			var remaining_amount = flt(frm.doc.grand_total) - flt(frm.doc.total_advance) - flt(frm.doc.write_off_amount);
			if (frm.doc.grand_total && (remaining_amount < loyalty_amount)) {
				let redeemable_points = parseInt(remaining_amount/frm.redemption_conversion_factor);
				frappe.throw(__("You can only redeem max {0} points in this order.",[redeemable_points]));
			}
			frm.set_value("loyalty_amount", loyalty_amount);
		}
	}
});