// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


{% include 'erpnext/selling/sales_common.js' %}

frappe.ui.form.on('Quotation', {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Sales Order': 'Make Sales Order'
		}
	},

	refresh: function(frm) {
		frm.trigger("set_label");
	},

	quotation_to: function(frm) {
		frm.trigger("set_label");
	},

	set_label: function(frm) {
		frm.fields_dict.customer_address.set_label(__(frm.doc.quotation_to + " Address"));
	}
});

erpnext.selling.QuotationController = erpnext.selling.SellingController.extend({
	onload: function(doc, dt, dn) {
		var me = this;
		this._super(doc, dt, dn);
		if(doc.customer && !doc.quotation_to)
			doc.quotation_to = "Customer";
		else if(doc.lead && !doc.quotation_to)
			doc.quotation_to = "Lead";

	},
	refresh: function(doc, dt, dn) {
		this._super(doc, dt, dn);
		doctype = doc.quotation_to == 'Customer' ? 'Customer':'Lead';
		frappe.dynamic_link = {doc: this.frm.doc, fieldname: doctype.toLowerCase(), doctype: doctype}

		var me = this;

		if (doc.__islocal && !doc.valid_till) {
			if(frappe.boot.sysdefaults.quotation_valid_till){
				this.frm.set_value('valid_till', frappe.datetime.add_days(doc.transaction_date, frappe.boot.sysdefaults.quotation_valid_till));
			} else {
				this.frm.set_value('valid_till', frappe.datetime.add_months(doc.transaction_date, 1));
			}
		}

		if(doc.docstatus == 1 && doc.status!=='Lost') {
			if(!doc.valid_till || frappe.datetime.get_diff(doc.valid_till, frappe.datetime.get_today()) >= 0) {
				cur_frm.add_custom_button(__('Sales Order'),
					cur_frm.cscript['Make Sales Order'], __('Create'));
			}

			if(doc.status!=="Ordered") {
				cur_frm.add_custom_button(__('Set as Lost'),
					cur_frm.cscript['Declare Order Lost']);
			}

			if(!doc.auto_repeat) {
				cur_frm.add_custom_button(__('Subscription'), function() {
					erpnext.utils.make_subscription(doc.doctype, doc.name)
				}, __('Create'))
			}

			cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
		}

		if (this.frm.doc.docstatus===0) {
			this.frm.add_custom_button(__('Opportunity'),
				function() {
					var setters = {};
					if(me.frm.doc.customer) {
						setters.customer = me.frm.doc.customer || undefined;
					} else if (me.frm.doc.lead) {
						setters.lead = me.frm.doc.lead || undefined;
					}
					erpnext.utils.map_current_doc({
						method: "erpnext.crm.doctype.opportunity.opportunity.make_quotation",
						source_doctype: "Opportunity",
						target: me.frm,
						setters: setters,
						get_query_filters: {
							status: ["not in", ["Lost", "Closed"]],
							company: me.frm.doc.company,
							// cannot set opportunity_type as setter, as the fieldname is order_type
							opportunity_type: me.frm.doc.order_type,
						}
					})
				}, __("Get items from"), "btn-default");
		}

		this.toggle_reqd_lead_customer();

	},

	quotation_to: function() {
		var me = this;
		if (this.frm.doc.quotation_to == "Lead") {
			this.frm.set_value("customer", null);
			this.frm.set_value("contact_person", null);
		} else if (this.frm.doc.quotation_to == "Customer") {
			this.frm.set_value("lead", null);
		}

		this.toggle_reqd_lead_customer();
	},

	toggle_reqd_lead_customer: function() {
		var me = this;

		this.frm.toggle_reqd("lead", this.frm.doc.quotation_to == "Lead");
		this.frm.toggle_reqd("customer", this.frm.doc.quotation_to == "Customer");

		// to overwrite the customer_filter trigger from queries.js
		this.frm.set_query('customer_address', erpnext.queries.address_query);
		this.frm.set_query('shipping_address_name', erpnext.queries.address_query);
	},

	tc_name: function() {
		this.get_terms();
	},

	validate_company_and_party: function(party_field) {
		if(!this.frm.doc.quotation_to) {
			frappe.msgprint(__("Please select a value for {0} quotation_to {1}", [this.frm.doc.doctype, this.frm.doc.name]));
			return false;
		} else if (this.frm.doc.quotation_to == "Lead") {
			return true;
		} else {
			return this._super(party_field);
		}
	},

	lead: function() {
		var me = this;
		if(!this.frm.doc.lead) {
			return;
		}

		frappe.call({
			method: "erpnext.crm.doctype.lead.lead.get_lead_details",
			args: {
				'lead': this.frm.doc.lead,
				'posting_date': this.frm.doc.transaction_date,
				'company': this.frm.doc.company,
			},
			callback: function(r) {
				if(r.message) {
					me.frm.updating_party_details = true;
					me.frm.set_value(r.message);
					me.frm.refresh();
					me.frm.updating_party_details = false;

				}
			}
		})
	}
});

cur_frm.script_manager.make(erpnext.selling.QuotationController);

cur_frm.fields_dict.lead.get_query = function(doc,cdt,cdn) {
	return{	query: "erpnext.controllers.queries.lead_query" }
}

cur_frm.cscript['Make Sales Order'] = function() {
	frappe.model.open_mapped_doc({
		method: "erpnext.selling.doctype.quotation.quotation.make_sales_order",
		frm: cur_frm
	})
}

cur_frm.cscript['Declare Order Lost'] = function(){
	var dialog = new frappe.ui.Dialog({
		title: __('Set as Lost'),
		fields: [
			{"fieldtype": "Text", "label": __("Reason for losing"), "fieldname": "reason",
				"reqd": 1 },
			{"fieldtype": "Button", "label": __("Update"), "fieldname": "update"},
		]
	});

	dialog.fields_dict.update.$input.click(function() {
		var args = dialog.get_values();
		if(!args) return;
		return cur_frm.call({
			method: "declare_order_lost",
			doc: cur_frm.doc,
			args: args,
			callback: function(r) {
				if(r.exc) {
					frappe.msgprint(__("There were errors."));
					return;
				}
				dialog.hide();
				cur_frm.refresh();
			},
			btn: this
		})
	});
	dialog.show();

}

frappe.ui.form.on("Quotation Item", "items_on_form_rendered", "packed_items_on_form_rendered", function(frm, cdt, cdn) {
	// enable tax_amount field if Actual
})

frappe.ui.form.on("Quotation Item", "stock_balance", function(frm, cdt, cdn) {
	var d = frappe.model.get_doc(cdt, cdn);
	frappe.route_options = {"item_code": d.item_code};
	frappe.set_route("query-report", "Stock Balance");
})
