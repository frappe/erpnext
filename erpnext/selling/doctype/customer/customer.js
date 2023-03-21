// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Customer", {
	setup: function(frm) {

		frm.make_methods = {
			'Quotation': () => frappe.model.open_mapped_doc({
				method: "erpnext.selling.doctype.customer.customer.make_quotation",
				frm: cur_frm
			}),
			'Opportunity': () => frappe.model.open_mapped_doc({
				method: "erpnext.selling.doctype.customer.customer.make_opportunity",
				frm: cur_frm
			})
		}

		frm.add_fetch('lead_name', 'company_name', 'customer_name');
		frm.add_fetch('default_sales_partner','commission_rate','default_commission_rate');
		frm.set_query('customer_group', {'is_group': 0});
		frm.set_query('default_price_list', { 'selling': 1});
		frm.set_query('account', 'accounts', function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			var filters = {
				'account_type': 'Receivable',
				'company': d.company,
				"is_group": 0
			};

			if(doc.party_account_currency) {
				$.extend(filters, {"account_currency": doc.party_account_currency});
			}
			return {
				filters: filters
			}
		});

		if (frm.doc.__islocal == 1) {
			frm.set_value("represents_company", "");
		}

		frm.set_query('customer_primary_contact', function(doc) {
			return {
				query: "erpnext.selling.doctype.customer.customer.get_customer_primary_contact",
				filters: {
					'customer': doc.name
				}
			}
		})
		frm.set_query('customer_primary_address', function(doc) {
			return {
				filters: {
					'link_doctype': 'Customer',
					'link_name': doc.name
				}
			}
		})

		frm.set_query('default_bank_account', function() {
			return {
				filters: {
					'is_company_account': 1
				}
			}
		});
	},
	customer_primary_address: function(frm){
		if(frm.doc.customer_primary_address){
			frappe.call({
				method: 'frappe.contacts.doctype.address.address.get_address_display',
				args: {
					"address_dict": frm.doc.customer_primary_address
				},
				callback: function(r) {
					frm.set_value("primary_address", r.message);
				}
			});
		}
		if(!frm.doc.customer_primary_address){
			frm.set_value("primary_address", "");
		}
	},

	is_internal_customer: function(frm) {
		if (frm.doc.is_internal_customer == 1) {
			frm.toggle_reqd("represents_company", true);
		}
		else {
			frm.toggle_reqd("represents_company", false);
		}
	},

	customer_primary_contact: function(frm){
		if(!frm.doc.customer_primary_contact){
			frm.set_value("mobile_no", "");
			frm.set_value("email_id", "");
		}
	},

	loyalty_program: function(frm) {
		if(frm.doc.loyalty_program) {
			frm.set_value('loyalty_program_tier', null);
		}
	},

	refresh: function(frm) {
		frm.dashboard.links_area.hide();
		frm.dashboard.heatmap_area.hide();
		if(frappe.defaults.get_default("cust_master_name")!="Naming Series") {
			frm.toggle_display("naming_series", false);
		} else {
			erpnext.toggle_naming_series();
		}

		frappe.dynamic_link = {doc: frm.doc, fieldname: 'name', doctype: 'Customer'}

		if(!frm.doc.__islocal) {
			frappe.contacts.render_address_and_contact(frm);

			// custom buttons

			/* frm.add_custom_button(__('Accounts Receivable'), function () {
				frappe.set_route('query-report', 'Accounts Receivable', {customer:frm.doc.name});
			}, __('View'));

			frm.add_custom_button(__('Accounting Ledger'), function () {
				frappe.set_route('query-report', 'General Ledger',
					{party_type: 'Customer', party: frm.doc.name});
			}, __('View'));

			frm.add_custom_button(__('Pricing Rule'), function () {
				erpnext.utils.make_pricing_rule(frm.doc.doctype, frm.doc.name);
			}, __('Create'));

			frm.add_custom_button(__('Get Customer Group Details'), function () {
				frm.trigger("get_customer_group_details");
			}, __('Actions'));

			if (cint(frappe.defaults.get_default("enable_common_party_accounting"))) {
				frm.add_custom_button(__('Link with Supplier'), function () {
					frm.trigger('show_party_link_dialog');
				}, __('Actions'));
			} */

			// indicator
			erpnext.utils.set_party_dashboard_indicators(frm);

		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}
		var grid = cur_frm.get_field("sales_team").grid;
		grid.set_column_disp("allocated_amount", false);
		grid.set_column_disp("incentives", false);
	},
	validate: function(frm) {
		if(frm.doc.lead_name) frappe.model.clear_doc("Lead", frm.doc.lead_name);

	},
	get_customer_group_details: function(frm) {
		frappe.call({
			method: "get_customer_group_details",
			doc: frm.doc,
			callback: function() {
				frm.refresh();
			}
		});
	},
	show_party_link_dialog: function(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __('Select a Supplier'),
			fields: [{
				fieldtype: 'Link', label: __('Supplier'),
				options: 'Supplier', fieldname: 'supplier', reqd: 1
			}],
			primary_action: function({ supplier }) {
				frappe.call({
					method: 'erpnext.accounts.doctype.party_link.party_link.create_party_link',
					args: {
						primary_role: 'Customer',
						primary_party: frm.doc.name,
						secondary_party: supplier
					},
					freeze: true,
					callback: function() {
						dialog.hide();
						frappe.msgprint({
							message: __('Successfully linked to Supplier'),
							alert: true
						});
					},
					error: function() {
						dialog.hide();
						frappe.msgprint({
							message: __('Linking to Supplier Failed. Please try again.'),
							title: __('Linking Failed'),
							indicator: 'red'
						});
					}
				});
			},
			primary_action_label: __('Create Link')
		});
		dialog.show();
	},
});

frappe.ui.form.on('Customer',  {
	after_save : function(frm) {
		// update customer Address  automatiicaly that details update in Address
		var phone,country,city,state,pincode,address_line1,address_line2;
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Address",
				filters: [
					["address_title", "=", frm.doc.customer_name],
				],
				fields: [
					"phone",
					"country",
					"city",
					"state",
					"pincode",
					"address_line1",
					"address_line2",
					"name",
				]
			},
			callback: function (r) {
				
				phone = (r.message[0].phone);
				country = (r.message[0].country);
				city = (r.message[0].city);
				state = (r.message[0].state);
				pincode = (r.message[0].pincode);
				address_line1 = (r.message[0].address_line1);
				address_line2 = (r.message[0].address_line2);
				var address_title = r.message[0].name

				if ((phone != frm.doc.landline) ||(country != frm.doc.country) || (state != frm.doc.state) || (pincode != frm.doc.pincode || frm.doc.pincode == undefined) || (address_line1 != frm.doc.address_line_1 || frm.doc.address_line_2== undefined) || (address_line2 != frm.doc.address_line_2 || frm.doc.address_line_2== undefined))
				{
					frappe.call({
						"method": "frappe.client.set_value",
						"args": {
							"doctype": "Address",
							"name": address_title,
							"fieldname": {
								"phone": frm.doc.landline,
								"country": frm.doc.country,
								"city": frm.doc.city,		
								"state": frm.doc.state,
								"pincode": frm.doc.pincode,
								"address_line1": frm.doc.address_line1,		
								"address_line2": frm.doc.address_line2,							
							},
						}
					});
				}
			}
		});
// update customer contact person details  automatiicaly that details update in customer contact person
		$.each(cur_frm.doc.customer_contact_person_details || [], function (i, v) {
			if(v.contact_name){
				var primary_email_id,designation,primary_mobile_number,department,person_name;
				frappe.call({
					method: "frappe.client.get_list",
					async:false,
					args: {
						doctype: "Customer Contact Person",
						filters: [
							["name", "=", v.contact_name],
						],
						fields: [
							"designation",
							"department",
							"primary_mobile_number",
							"primary_email_id",
							"name",
						]
					},
					callback: function (r) {
						designation = (r.message[0].designation);
						department = (r.message[0].department);
						primary_mobile_number = (r.message[0].primary_mobile_number);
						primary_email_id = (r.message[0].primary_email_id);
						person_name = r.message[0].name

						if ((primary_email_id && primary_email_id != v.primary_email_id ||(city != frm.doc.city) || (primary_email_id == "" || primary_email_id == undefined)) || (designation && designation != v.designation|| (designation == "" || designation == undefined)) || (department && department != v.department|| (department == "" || department == undefined)) || (primary_mobile_number && primary_mobile_number != v.primary_mobile_number|| (primary_mobile_number == "" || primary_mobile_number == undefined))){
							frappe.call({
								"method": "frappe.client.set_value",
								"args": {
									"doctype": "Customer Contact Person",
									"name": person_name,
									"fieldname": {
										"primary_email_id": v.primary_email_id,
										"designation": v.designation,
										"department": v.department,		
										"primary_mobile_number": v.primary_mobile_number						
									},
								}
							});
						}
					}
				});
			}
		})	
		window.location.reload(1);
	},
	country: function(frm){
        frm.set_value('city', null)
		frm.set_value('state',null)
		frm.set_query('city',function(){
			return {
				filters: {
					'country': frm.doc.country,
				}
			}
		})
    },
	state:function(frm){
		frm.set_value("city", null)
		frm.set_query('city', function() {
			return {
				filters: {
					'state': frm.doc.state,
				}
			}
		});
	},
	region: function(frm) {
		frm.set_value('state', null)
		frm.set_query('state', function(){
			return {
				filters: {
					'country': frm.doc.country,
					'region': frm.doc.region
				}
			}
		})
	},
	refresh: function (frm) {
		frm.set_df_property('customer_contact_person_details', 'cannot_add_rows', true);
		frm.fields_dict["customer_contact_person_details"].grid.add_custom_button(__('Create Contact Person Details'),
	
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
					width: "50%"
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
					method:"erpnext.selling.doctype.customer.customer.contact_person",
					args: {
						customer_name: frm.doc.customer_name,
						person_name:(values["Person_name"]),
						designation:(values["designation"]),
						department:(values["department"]),
						primary_mobile_number:(values["primary_mobile_number"]),
						primary_email_id:(values["primary_email_id"]),
						customer_region_for_filter_conact_person:frm.doc.region,
					},
				})
				let customer_contact_person_details  = frm.add_child("customer_contact_person_details");
				customer_contact_person_details.person_name = (values["Person_name"])
				customer_contact_person_details.department = (values["department"])
				customer_contact_person_details.designation = (values["designation"])
				customer_contact_person_details.primary_mobile_number = (values["primary_mobile_number"])
				customer_contact_person_details.primary_email_id = (values["primary_email_id"])
				customer_contact_person_details.primary_email_id = (values["primary_email_id"])
				refresh_field("customer_contact_person_details")
				d.hide();
				window.location.reload(1);
			}
		    })
		    d.show();  
		    } );
		    frm.fields_dict["customer_contact_person_details"].grid.grid_buttons.find('.btn-custom').removeClass('btn-default').addClass('btn-primary new-custom-btn');
		//once delete customer then delete there address,delete customer child table and customer form also delete
	},
})
frappe.ui.form.on("Customer Contact Person Details",{
// if customer_contact_person_delect then delect that person in customer contact person
	before_customer_contact_person_details_remove:function(frm,cdt,cdn){
		var row = locals[cdt][cdn];
		if (row.person_name== "" || row.contact_name == ""){
			customer_contact_person_details_remove();
		}
		if (row.contact_name){
			frappe.call({
				method: "erpnext.selling.doctype.customer.customer.remove_person",
				async:false,
				args: {
					name: row.contact_name,
				}
			})
		}
		frm.save();
	},
	add_secondary_contact_details: function(frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);	
		frappe.set_route("Form", "Customer Contact Person", row.contact_name);
	},
 });