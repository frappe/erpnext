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

	landline:function (frm){
		var phone;
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Address",
				filters: [
					["address_title", "=", frm.doc.customer_name],
				],
				fields: [
					"phone",
					"name",
				]
			},
			callback: function (r) {	
				phone = (r.message.phone);

				var address_title = r.message[0].name
				if (phone != frm.doc.landline || phone == undefined) {
					frappe.db.set_value("Address", address_title, "phone", frm.doc.landline)
					setInterval(() => {
                        cur_frm.save();
                	}, 300000); 
				}
			}	
		});	
	},
	country:function (frm){
		var country;
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Address",
				filters: [
					["address_title", "=", frm.doc.customer_name],
				],
				fields: [
					"country",
					"name",
				]
			},
			callback: function (r) {	
				country = (r.message[0].country);

				var address_title = r.message[0].name
				if (country != frm.doc.country) {
					frappe.db.set_value("Address", address_title, "country", frm.doc.country)	
					setInterval(() => {
                        cur_frm.save();
                	}, 300000); 
				}
			}	
		});	
	},
	city:function (frm){
		var city;
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Address",
				filters: [
					["address_title", "=", frm.doc.customer_name],
				],
				fields: [
					"city",
					"name",
				]
			},
			callback: function (r) {	
				city = (r.message[0].city);

				var address_title = r.message[0].name
				if (city != frm.doc.city) {
					frappe.db.set_value("Address", address_title, "city", frm.doc.city)	
					setInterval(() => {
                        cur_frm.save();
                	}, 300000); 			
				}
			}	
		});	
	},
	state:function (frm){
		var state;
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Address",
				filters: [
					["address_title", "=", frm.doc.customer_name],
				],
				fields: [
					"state",
					"name",
				]
			},
			callback: function (r) {	
				state = (r.message[0].state);

				var address_title = r.message[0].name
				if (state != frm.doc.state) {
					frappe.db.set_value("Address", address_title, "state", frm.doc.state)	
					setInterval(() => {
                        cur_frm.save();
                	}, 300000); 			
				}
			}	
		});	
	},
	pincode:function (frm){
		var pincode;
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Address",
				filters: [
					["address_title", "=", frm.doc.customer_name],
				],
				fields: [
					"pincode",
					"name",
				]
			},
			callback: function (r) {	
				pincode = (r.message[0].pincode);

				var address_title = r.message[0].name
				if (pincode != frm.doc.pincode) {
					frappe.db.set_value("Address", address_title, "pincode", frm.doc.pincode)	
					setInterval(() => {
                        cur_frm.save();
                	}, 300000); 			
				}
			}	
		});	
	},
	address_line1:function (frm){
		var address_line1;
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Address",
				filters: [
					["address_title", "=", frm.doc.customer_name],
				],
				fields: [
					"address_line1",
					"name",
				]
			},
			callback: function (r) {	
				address_line1 = (r.message[0].address_line1);

				var address_title = r.message[0].name
				if (address_line1 != frm.doc.address_line1) {
					frappe.db.set_value("Address", address_title, "address_line1", frm.doc.address_line1)	
					setInterval(() => {
                        cur_frm.save();
                	}, 300000); 			
				}
			}	
		});	
	},
	address_line2:function (frm){
		var address_line2;
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Address",
				filters: [
					["address_title", "=", frm.doc.customer_name],
				],
				fields: [
					"address_line2",
					"name",
				]
			},
			callback: function (r) {	
				address_line2 = (r.message[0].address_line2);

				var address_title = r.message[0].name
				if (address_line2 != frm.doc.address_line2 || frm.doc.address_line2 == "" ) {
					frappe.db.set_value("Address", address_title, "address_line2", frm.doc.address_line2)	
					setInterval(() => {
                        cur_frm.save();
                	}, 300000); 			
				}
			}	
		});	
	},
});


frappe.ui.form.on('Customer',  {
	after_save : function(frm) {
		var last_row;


		//create new entry in contact person 
		var arr =[];
		var arr1 =[];
		var arr2 =[];
		var arr3 =[];
		var arr4=[];
		var doc2 = cur_frm.doc.customer_contact_person_details;
		$.each(cur_frm.doc.customer_contact_person_details || [], function (i, row) {
			
			arr.push(row.person_name)
			arr1.push(row.designation)
			arr2.push(row.primary_email_id)
			arr3.push(row.department)
			arr4.push(row.primary_mobile_number)
			console.log(arr);
		})
		last_row = doc2[arr.length-1]

		console.log("last_row",last_row);
		if (!last_row.contact_name){
			frappe.call({
				async:false,
				method:"erpnext.selling.doctype.customer.customer.contact_person",
				args: {
					customer_name: frm.doc.customer_name,
					
					person_name:arr[arr.length-1],
					designation:arr1[arr1.length-1],
					primary_email_id:arr2[arr2.length-1],
					department:arr3[arr3.length-1],
					primary_mobile_number:arr4[arr4.length-1]
			
				},		
			})

			frappe.call({
				method:"erpnext.selling.doctype.customer.customer.last_document",
				async:false,
				callback: function (r) {
						console.log(r)
						last_row.contact_name = r.message;
						console.log("last_row.person_name",last_row.person_name);
				}

			})
		}
			
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


						if ((primary_email_id && primary_email_id != v.primary_email_id || (primary_email_id == "" || primary_email_id == undefined)) || (designation && designation != v.designation|| (designation == "" || designation == undefined)) || (department && department != v.department|| (department == "" || department == undefined)) || (primary_mobile_number && primary_mobile_number != v.primary_mobile_number|| (primary_mobile_number == "" || primary_mobile_number == undefined))){
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
	},
	country(frm){
        frappe.call({
            method: "axis_india_app.Countrydata.countrydata.cities_in_country", 
            args: {
              country: frm.doc.country
            }, 
            
            callback: function(r) {
              frm.set_df_property("state", "options", r.message)
            }
          })
    },
})


	
frappe.ui.form.on("Customer Contact Person Details",{
	
	before_customer_contact_person_details_remove:function(frm,cdt,cdn){
		var row = locals[cdt][cdn];
		console.log("row",row.contact_name);
		frappe.call({
				method: "erpnext.selling.doctype.customer.customer.remove_person",
				async:false,
				args: {
					name: row.contact_name,
				}

			})
	}
 });