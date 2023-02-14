// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext");
cur_frm.email_field = "email_id";

erpnext.LeadController = frappe.ui.form.Controller.extend({
	setup: function () {
		this.frm.make_methods = {
			'Customer': this.make_customer,
			'Quotation': this.make_quotation,
			'Opportunity': this.make_opportunity
		};

		this.frm.toggle_reqd("lead_name", !this.frm.doc.organization_lead);
	},

	onload: function () {
		this.frm.set_query("customer", function (doc, cdt, cdn) {
			return { query: "erpnext.controllers.queries.customer_query" }
		});

		this.frm.set_query("lead_owner", function (doc, cdt, cdn) {
			return { query: "frappe.core.doctype.user.user.user_query" }
		});

		this.frm.set_query("contact_by", function (doc, cdt, cdn) {
			return { query: "frappe.core.doctype.user.user.user_query" }
		});
	},

	refresh: function () {
		let doc = this.frm.doc;
		erpnext.toggle_naming_series();
		frappe.dynamic_link = { doc: doc, fieldname: 'name', doctype: 'Lead' }
		
		// on open status show contatced,close,Success Button 
		if (doc.status==="Open") {
			if (doc.status != "Contacted") {
				this.frm.add_custom_button(__('Contacted'), () => this.contacted_lead(), __("Status"));
			}		
		}
		if (doc.status==="Open" || doc.status == "Contacted" ){
			this.frm.add_custom_button(__('Success'), () => this.success_lead(), __("Status"));
		}
		if ( doc.status==="Open" || doc.status == "Contacted") {
			this.frm.add_custom_button(__('Close'), () => this.close_lead(), __("Status"));
		}
		
		//if status is contacted substatus button created[Note if sub-status On Call Discussion then after save On Call Discussion option remove from sub-status list]
		if (doc.status == "Contacted"){
			if (doc.sub_status == "" ){
				this.frm.add_custom_button(__("On Call Discussion"), () => this.on_call_discussion_lead(), __("Sub-Status"));
			}
			if ((!in_list(["Technical Visit"],doc.sub_status)&& doc.sub_status == "On Call Discussion")||doc.sub_status == "" ){
				this.frm.add_custom_button(__("Technical Visit"), () => this.technical_visit_lead(), __("Sub-Status"));
			}	
			if ((!in_list(["Quotation"],doc.sub_status)&& in_list(["Technical Visit","On Call Discussion"],doc.sub_status))||doc.sub_status == "" ){
				this.frm.add_custom_button(__("Quotation"), () => this.quotation_lead(), __("Sub-Status"));
			}	
			if ((!in_list(["Follow Up"],doc.sub_status)&& in_list(["Technical Visit","On Call Discussion","Quotation"],doc.sub_status))||doc.sub_status == "" ){
				this.frm.add_custom_button(__("Follow Up"), () => this.follow_up_visit_lead(), __("Sub-Status"));
			}	
			if ((!in_list(["Budgetary  Discussion"],doc.sub_status)&& in_list(["Technical Visit","On Call Discussion","Quotation","Follow Up"],doc.sub_status))||doc.sub_status == "" ){
				this.frm.add_custom_button(__("Budgetary  Discussion"), () => this.budgetary_discussion_lead(), __("Sub-Status"));
			}	
			if ((!in_list(["Negotiation"],doc.sub_status)&& in_list(["Technical Visit","On Call Discussion","Quotation","Follow Up","Budgetary  Discussion"],doc.sub_status))||doc.sub_status == "" ){
				this.frm.add_custom_button(__("Negotiation"), () => this.negotiation_lead(), __("Sub-Status"));
			}	
		}

		/* if (!this.frm.is_new() && doc.__onload && !doc.__onload.is_customer) {
			this.frm.add_custom_button(__("Customer"), this.make_customer, __("Create"));
			this.frm.add_custom_button(__("Opportunity"), this.make_opportunity, __("Create"));
			this.frm.add_custom_button(__("Quotation"), this.make_quotation, __("Create"));
		}
 */
		if (!this.frm.is_new()) {
			frappe.contacts.render_address_and_contact(this.frm);
		} else {
			frappe.contacts.clear_address_and_contact(this.frm);
		}
	},

	contacted_lead: function(){
		cur_frm.set_value("status","Contacted");
		cur_frm.save();
	},
	on_call_discussion_lead: function(){
		cur_frm.set_value("sub_status","On Call Discussion");
		cur_frm.save();
	},
	technical_visit_lead: function(){
		cur_frm.set_value("sub_status","Technical Visit");
		cur_frm.save();
	},
	quotation_lead: function(){
		cur_frm.set_value("sub_status","Quotation");
		cur_frm.save();
	},
	follow_up_visit_lead: function(){
		cur_frm.set_value("sub_status","Follow Up");
		cur_frm.save();
	},
	budgetary_discussion_lead: function(){
		cur_frm.set_value("sub_status","Budgetary  Discussion");
		cur_frm.save();
	},
	negotiation_lead: function(){
		cur_frm.set_value("sub_status","Negotiation");
		cur_frm.save();
	},
	success_lead: function(){
		cur_frm.set_value("status","Success");
		cur_frm.save();
	},
	close_lead: function(){
		cur_frm.set_value("status","Close");
		cur_frm.save();
	},

	make_customer: function () {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.lead.lead.make_customer",
			frm: cur_frm
		})
	},

	make_opportunity: function () {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.lead.lead.make_opportunity",
			frm: cur_frm
		})
	},

	make_quotation: function () {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.lead.lead.make_quotation",
			frm: cur_frm
		})
	},

	/* organization_lead: function () {
		this.frm.toggle_reqd("lead_name", !this.frm.doc.organization_lead);
		this.frm.toggle_reqd("company_name", this.frm.doc.organization_lead);
	}, */

	company_name: function () {
		if (this.frm.doc.organization_lead && !this.frm.doc.lead_name) {
			this.frm.set_value("lead_name", this.frm.doc.company_name);
		}
	},

	contact_date: function () {
		if (this.frm.doc.contact_date) {
			let d = moment(this.frm.doc.contact_date);
			d.add(1, "day");
			this.frm.set_value("ends_on", d.format(frappe.defaultDatetimeFormat));
		}
	},

});

$.extend(cur_frm.cscript, new erpnext.LeadController({ frm: cur_frm }));

frappe.ui.form.on('Lead', {
	//In company base person will filter show in child table
	setup: (frm) => {
		frm.fields_dict["lead_contact_person_details"].grid.get_field("person_name").get_query = function(doc, cdt, cdn) {
			return {
				filters: {'customer_name': doc.customer_name}
			}
		};
		frm.set_query('customer_name', function(doc) {
			return {
				filters: {
					"region"  : getCurrentUserRegion()
				}

			}
			
		});
		function getCurrentUserRegion()
		{  
			var ret_value = "";
			frappe.call({                        
				method: "frappe.client.get_value", 
				async:false,
				args: { 
					    doctype: "User",
					    name:frappe.session.user,
					    fieldname:"region",
					  },
				callback: function(r) {
                    ret_value=r.message.region;
				}	 
		 	});
			return ret_value;
		}
	},
	
	// hide connection section, doc name set in lead number,if status is Success/Close then disable save button from form
	refresh(frm) {
		frm.dashboard.links_area.hide();
		if(frm.doc.name  && !frm.doc.__islocal && (frm.doc.lead_number == null || frm.doc.lead_number == undefined)){
			cur_frm.set_value("lead_number",frm.doc.name);
			frm.save();
		}
		if (frm.doc.status === "Success" || frm.doc.status === "Close" ){
			frm. disable_save()
		}
	},
	//form is save then set status Open, if company name mention then person child table set Mandatory 
	before_save :function(frm){
		if (frm.doc.__islocal)
		{
			cur_frm.set_value("status","Open");
		}
	/* 	if (frm.doc.company_name !=""){
			frm.set_df_property('lead_contact_person_details', 'reqd', 1);
		} */
	},
	//if status is Success then in company details doctype Existing customer set check
	after_save :function(frm){
		if (frm.doc.status === "Success"){
			frappe.db.set_value("Customer", frm.doc.customer_name, "existing_customer", 1)
		}
	},
	//on lead transfer create 1 Dialog box for Reason in lead_assing_to_user child table add user name,assing to mail, lead transfer Reason,today date time  
 	lead_transfer:function(frm){
		if(!frm.doc.__islocal){// add here len of child table if it 1 not show following message after that shown
			var d = new frappe.ui.Dialog({
			
				title: __('Reason for Transfer Lead Other User'),
				fields: [
					{
						"fieldname": "reason_lead_transfer",
						"fieldtype": "Text",
						"reqd": 1,
					}
				],
				primary_action_label: 'Submit',
				primary_action(value) {
					console.log(value["reason_lead_transfer"]);
					lead_assign_to_user.lead_transfer_reason = (value["reason_lead_transfer"]);
					refresh_field("lead_assign_to_user");
					frm.save();
					d.hide();
				}
			})
			d.show();
			console.log(d);
		}
		var date = frappe.datetime.now_datetime();
		lead_assign_to_user.assign_email = frm.doc.lead_transfer
		lead_assign_to_user.date = date
		lead_assign_to_user.user_name = frm.doc.lead_transfer_user_full_name
		refresh_field("lead_assign_to_user")
	}

});				
