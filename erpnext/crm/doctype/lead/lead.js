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
		setTimeout(function(){
			window.location.reload(1);
		}, 500);
	},
	close_lead: function(){
		cur_frm.set_value("status","Close");
		cur_frm.save();
		setTimeout(function(){
			window.location.reload(1);
		}, 500);
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
		if(!frm.doc.__islocal){
			frappe.call({                        
				method: "erpnext.crm.doctype.lead.lead.user_created", 
				async:false,
				args: { 
					name:frm.docname,
					user_created_by : frm.doc.users,
					lead_transfer : frm.doc.lead_transfer
					},	 
		 	});
		}
	},
	setup: (frm) => {
		frm.events.get_customer_contact_person_list(frm);
	},
	//on lead transfer create 1 Dialog box for Reason in lead_assing_to_user child table add user name,assing to mail, lead transfer Reason,today date time  
	lead_transfer:function(frm){
		let lead_assign_to_user  = frm.add_child("lead_assign_to_user");
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
					lead_assign_to_user.lead_transfer_reason = (value["reason_lead_transfer"]);
					refresh_field("lead_assign_to_user");
					frm.save();
					d.hide();
				}
			})
			d.show();
		}
		var date = frappe.datetime.now_datetime();
		lead_assign_to_user.assign_email = frm.doc.lead_transfer
		lead_assign_to_user.date = date
		lead_assign_to_user.user_name = frm.doc.lead_transfer_user_full_name
		refresh_field("lead_assign_to_user")
	},
	customer_name: function(frm) {
		if (frm.doc.customer_name === "" || frm.doc.customer_name != "") {
			frm.clear_table("lead_contact_person_details");
			frm.refresh_fields();
		}
		frm.events.get_customer_contact_person_list(frm);
	},
	// get selected customer table list
	get_customer_contact_person_list:function(frm){
		if(frm.doc.customer_name){
			frappe.call({
				method: "erpnext.crm.doctype.lead.lead.get_customer_name_details",
				async:false,
				args: {customer_name:frm.doc.customer_name},
				callback: function(r) {
					var df = frappe.meta.get_docfield("Lead Contact Person Details","person_name", cur_frm.doc.name);
					df.options = r.message;
				}
			})
		}
	},
		//if row is empty and try to add row they now allow after fill that empty row then they allow to add new row
	add_person: function (frm) {
		var arr=[];
		if(frm.doc.lead_contact_person_details.length !=1){
			$.each(frm.doc.lead_contact_person_details || [], function (i, row) {
				arr.push(row.person_name)
			});		
			if(arr[arr.length-2] === undefined || arr[arr.length-2] === "" || arr[arr.length-2] === null){
					$.each(frm.doc.lead_contact_person_details || [], function (i, row) {

						if (i === arr.length-2){
							cur_frm.fields_dict["lead_contact_person_details"].grid.grid_rows[i].remove();		
					
						}
					});	
			} 
		}
	},
	//Create New Contact Person also create button on button click Dialog form will be pop after submit that form create new Contact Person and also add that Contact Person in visit table
	refresh: function(frm)  {

		frm.dashboard.links_area.hide();
		if(frm.doc.name  && !frm.doc.__islocal && (frm.doc.lead_number == null || frm.doc.lead_number == undefined)){
			cur_frm.set_value("lead_number",frm.doc.name);
			frm.save();
		}
		if (frm.doc.status === "Success" || frm.doc.status === "Close" ){
			frm. disable_save()
		}
		// hide connection section, doc name set in lead number,if status is Success/Close then disable save button from form

		frm.events.get_customer_contact_person_list(frm);

		if(frm.doc.status=== "Open" || frm.doc.status=== "Contacted"|| frm.doc.__islocal){
			
			frm.fields_dict["lead_contact_person_details"].grid.add_custom_button(__('Create Contact Person Details'),
	
		function() {
			var d = new frappe.ui.Dialog({
			title: __('Create New Contact Person'),
			fields: [	
				{
					label: 'Customer Name',
					fieldname: 'customer_name',
					fieldtype: 'Data',
					default: frm.doc.customer_name,
					read_only: 1,
					reqd: 1
				},
				{
					label: 'Person Name',
					fieldname: 'Person_name',
					fieldtype: 'Data',
					reqd: 1
				},
				{
					label: "Designation",
					fieldname: "designation",
					fieldtype: "Link",
					options: "Designation"
				},
				{
					fieldname: "column_break1",
					fieldtype: "Column Break",
				},
				{	
					label: "Division / Department",
					fieldname: "department",
					fieldtype: "Link",
					options: "Person Department"
				},
				{
					label: "Primary Email Id",
					fieldname: "primary_email_id",
					fieldtype: "Data",
					options: "Email",
					reqd: 1
				},
				{
					label: "Primary Mobile Number",
					fieldname: "primary_mobile_number",
					fieldtype: "Data",
					options: "phone",
					reqd: 1,
				},
			],
			primary_action_label: 'Create',
			primary_action(values) {
				frappe.call({
					async:false,
					method:"axis_india_app.visit_module.doctype.visit.visit.contact_person",
					args: {
						customer_name: frm.doc.customer_name,
						person_name:(values["Person_name"]),
						designation:(values["designation"]),
						department:(values["department"]),
						primary_mobile_number:(values["primary_mobile_number"]),
						primary_email_id:(values["primary_email_id"]),
					},
				})
				frm.events.get_customer_contact_person_list(frm);
				let lead_contact_person_details  = frm.add_child("lead_contact_person_details");
				lead_contact_person_details.person_name = (values["Person_name"])
				lead_contact_person_details.department = (values["department"])
				lead_contact_person_details.designation = (values["designation"])
				lead_contact_person_details.primary_mobile_number = (values["primary_mobile_number"])
				lead_contact_person_details.primary_email_id = (values["primary_email_id"])
				lead_contact_person_details.primary_email_id = (values["primary_email_id"])
				refresh_field("lead_contact_person_details")
				d.hide();
			}
		    })
		    d.show();  
		    } );
		    frm.fields_dict["lead_contact_person_details"].grid.grid_buttons.find('.btn-custom').removeClass('btn-default').addClass('btn-primary new-custom-btn');
		}
	}
});				

frappe.ui.form.on("Lead Contact Person Details", {
	lead_contact_person_details_add:function(frm) {
		frm.events.add_person(frm);
	},
	//fetch select person name details
	person_name:function(frm,cdt,cdn) {
		var d = locals[cdt][cdn];
		frappe.db.get_value("Customer Contact Person", { "person_name": d.person_name}, ["designation", "department","primary_mobile_number","primary_email_id"],function (value){
			frappe.model.set_value(d.doctype, d.name, "designation", value.designation)
			frappe.model.set_value(d.doctype, d.name, "department", value.department)
			frappe.model.set_value(d.doctype, d.name, "primary_mobile_number", value.primary_mobile_number)
			frappe.model.set_value(d.doctype, d.name, "primary_email_id", value.primary_email_id)
			refresh_field('Customer Contact Person')
		});
	},
});
 