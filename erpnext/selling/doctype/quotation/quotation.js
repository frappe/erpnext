// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// Module CRM
// =====================================================================================
cur_frm.cscript.tname = "Quotation Item";
cur_frm.cscript.fname = "quotation_details";
cur_frm.cscript.other_fname = "other_charges";
cur_frm.cscript.sales_team_fname = "sales_team";

{% include 'selling/sales_common.js' %}
{% include 'accounts/doctype/sales_taxes_and_charges_master/sales_taxes_and_charges_master.js' %}
{% include 'utilities/doctype/sms_control/sms_control.js' %}
{% include 'accounts/doctype/sales_invoice/pos.js' %}

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
		
		if(doc.docstatus == 1 && doc.status!=='Lost') {
			cur_frm.add_custom_button(__('Make Sales Order'), 
				cur_frm.cscript['Make Sales Order']);
			if(doc.status!=="Ordered") {
				cur_frm.add_custom_button(__('Set as Lost'), 
					cur_frm.cscript['Declare Order Lost'], "icon-exclamation");
			}
			cur_frm.appframe.add_button(__('Send SMS'), cur_frm.cscript.send_sms, "icon-mobile-phone");
		}
		
		if (this.frm.doc.docstatus===0) {
			cur_frm.add_custom_button(__('From Opportunity'), 
				function() {
					frappe.model.map_current_doc({
						method: "erpnext.selling.doctype.opportunity.opportunity.make_quotation",
						source_doctype: "Opportunity",
						get_query_filters: {
							docstatus: 1,
							status: "Submitted",
							enquiry_type: cur_frm.doc.order_type,
							customer: cur_frm.doc.customer || undefined,
							lead: cur_frm.doc.lead || undefined,
							company: cur_frm.doc.company
						}
					})
				});
		}

		if (!doc.__islocal) {
			cur_frm.communication_view = new frappe.views.CommunicationList({
				list: frappe.get_list("Communication", {"parent": doc.name, "parenttype": "Quotation"}),
				parent: cur_frm.fields_dict.communication_html.wrapper,
				doc: doc,
				recipients: doc.contact_email
			});
		}
		
		this.quotation_to();
	},
	
	quotation_to: function() {
		var me = this;
		this.frm.toggle_reqd("lead", this.frm.doc.quotation_to == "Lead");
		this.frm.toggle_reqd("customer", this.frm.doc.quotation_to == "Customer");
		if (this.frm.doc.quotation_to == "Lead") {
			this.frm.set_value("customer", null);
			this.frm.set_value("contact_person", null);
			
			// to overwrite the customer_filter trigger from queries.js
			$.each(["customer_address", "shipping_address_name"], 
				function(i, opts) {
					me.frm.set_query(opts, erpnext.queries["lead_filter"]);
				}
			);
		}
		else if (this.frm.doc.quotation_to == "Customer")
			this.frm.set_value("lead", null);
	},

	tc_name: function() {
		this.get_terms();
	},
	
	validate_company_and_party: function(party_field) {
		if(!this.frm.doc.quotation_to) {
			msgprint(__("Please select a value for" + " " + 
				frappe.meta.get_label(this.frm.doc.doctype, "quotation_to", this.frm.doc.name)));
			return false;
		} else if (this.frm.doc.quotation_to == "Lead") {
			return true;
		} else {
			return this._super(party_field);
		}
	},
	
	lead: function() {
		var me = this;
		frappe.call({
			method: "erpnext.selling.doctype.lead.lead.get_lead_details",
			args: { "lead": this.frm.doc.lead },
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
		source_name: cur_frm.doc.name
	})
}

cur_frm.cscript['Declare Order Lost'] = function(){
	var dialog = new frappe.ui.Dialog({
		title: "Set as Lost",
		fields: [
			{"fieldtype": "Text", "label": __("Reason for losing"), "fieldname": "reason",
				"reqd": 1 },
			{"fieldtype": "Button", "label": __("Update"), "fieldname": "update"},
		]
	});

	dialog.fields_dict.update.$input.click(function() {
		args = dialog.get_values();
		if(!args) return;
		return cur_frm.call({
			method: "declare_order_lost",
			doc: cur_frm.doc,
			args: args.reason,
			callback: function(r) {
				if(r.exc) {
					msgprint(__("There were errors."));
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

cur_frm.cscript.on_submit = function(doc, cdt, cdn) {
	if(cint(frappe.boot.notification_settings.quotation))
		cur_frm.email_doc(frappe.boot.notification_settings.quotation_message);
}