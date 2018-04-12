frappe.pages['crm-dashboard'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'CRM Dashboard',
		single_column: true
	});

	frappe.ccc = new frappe.CallCenterConsole(wrapper);

	if (frappe.get_route()[1]) {
		page.wrapper.find('.txt-lookup').val(frappe.get_route()[1]);
		frappe.ccc.get_info();
	}
}

frappe.pages['crm-dashboard'].refresh = function(wrapper) {
	if (frappe.ccc && frappe.get_route()[1]) {
		wrapper.page.wrapper.find('.txt-lookup').val(frappe.get_route()[1]);
		frappe.ccc.get_info();
	}
}

// ===========================================may or may not need it==================================
function lookup_call_lead(content){
	var txt = content.find('#txt-lookup');
	var create_btn = content.find('#btn-create-lead');
	create_btn.click(function(r){
		frappe.call({
			method:"refreshednow_erpnext.ccc_api.create_lead",
			args:{
				caller_number: $(txt).val()
			},
			freeze: true,
			freeze_message: __("Looking up caller number..."),
			callback: function(r){
				//console.log(r.message);
				var raw_url = window.location.origin;
				//console.log(r.message);
				var str = "/desk#Form/Lead/"+r.message;
				var url = raw_url + str;
				window.location = url;
			}
		});

	});
}

function lookup_call_customer(content){
	var txt = content.find('#txt-lookup');
	var create_btn = content.find('#btn-create-customer');
	create_btn.click(function(r){
		frappe.prompt([
			{'fieldname': 'customer', 'fieldtype': 'Link', 'options':'Customer','label':'Customer'}
		],
		function(values){
			create_customer(values.customer, $(txt).val())
		},
		'Select Customer',
		'Select'
		)
	});
}

function create_customer(customer_name, caller_number){
	frappe.call({
			method:"refreshednow_erpnext.ccc_api.create_contact",
			args:{
				caller_number: caller_number,
				customer_name: customer_name
			},
			callback: function(r){
				//console.log(r.message);
				var raw_url = window.location.origin;
				var str = "/desk#Form/Contact/"+r.message;
				var url = raw_url + str;
				//var win = window.open(url);
				window.location = url;
			}
		});
}

function wireup_scheduling_button(content, wrapper) {
	var btn_allocate = content.find('#btn-open-scheduling');
	btn_allocate.on("click", function() {
		frappe.set_route("rn-team-scheduling");
	});	
}
// ===================================================================================================

frappe.CallCenterConsole = Class.extend({
	init: function(wrapper) {
		this.page = wrapper.page;
		this.make();
	},
	make: function() {
		var me = this;
		// me.page.add_inner_button(__("Search"), function() {
		// 	console.log("Search");
		// });
		//console.log("Content", me.page)

		var input_html = '<div class="jumbotron"><div class="input-group"><input type="text" class="form-control txt-lookup" placeholder="Search for caller number..."> <span class="input-group-btn"> <button id="btn-lookup" class="btn btn-secondary" type="button">Search!</button> </span> </div> </div><div class="clearfix"></div>'
		me.page.main.append(input_html);

		// var text = me.page.main.find(".txt-lookup");

		me.page.main.on("click", "button[id='btn-lookup']", function() {
			me.get_info();
		});

		me.page.main.on("keypress", ".txt-lookup", function(ev) {
			var keycode = (ev.keyCode ? ev.keyCode : ev.which);
            if (keycode == '13') {
				me.get_info();
            }
		});
	},
	get_info: function() {
		var me = this;
		var text = me.page.main.find(".txt-lookup");

		if (text.val() && !isNaN(text.val())) {
			frappe.call({
				method: "erpnext.crm.doctype.crm_settings.crm_settings.get_caller_info",
				args: { "caller_no": text.val().trim() },
				callback: function(r){
					if(r) {
						me.page.main.find("#cc_console").remove("#cc_console"); 
						console.log("R",r.message)
						content = frappe.render_template("telephony_console", {"info": r.message || null});
						me.page.main.append(content);
						
						if (r.message.title == "Lead") {
							me.page.main.find("#lead_to_customer").on("click", function() {
								me.create_customer(r.message);
							});
							me.page.main.find("#lead_issue").on("click", function() {
								me.create_issue(r.message);
							});
						} else if(r.message.title == "Customer") {
							me.page.main.find("#customer_issue").on("click", function() {
								me.create_issue(r.message);
							});
						} else {
							me.page.main.find("#new_lead").on("click", function() {
								me.create_lead(r.message);
							});
							me.page.main.find("#new_customer").on("click", function() {
								me.create_lead(r.message);
							});
							me.page.main.find("#new_caller_issue").on("click", function() {
								me.create_issue(r.message);
							});						
						}							
					}
				}
			});

		} else {
			frappe.show_alert("Please enter a valid number");
		}
	},
	create_lead: function(resp) {
		var new_lead = frappe.model.make_new_doc_and_get_name('Lead');
		new_lead = locals["Lead"][new_lead];
		new_lead.phone = resp.number;
		new_lead.contact_number = resp.number;
		new_lead.lead_name = resp.name;	
		new_lead.status = "Lead";	
		
		frappe.set_route("Form", "Lead", new_lead.name);
	},
	create_issue: function(resp) {
		console.log("Issue", resp);

		var new_issue = frappe.model.make_new_doc_and_get_name('Issue');
		new_issue = locals["Issue"][new_issue];
	

		if (resp.title == "Customer") {
			console.log("Setting customer", resp.customer);
			new_issue.subject = resp.name;
			new_issue.customer = resp.customer;
		} else if (resp.title == "Lead") {
			console.log("Setting lead", resp.lead_name);
			new_issue.subject = resp.lead_name;
			new_issue.lead = resp.name;
		} else {
			new_issue.subject = resp.title + "-" + resp.number;
		}

		frappe.set_route("Form", "Issue", new_issue.name);	
	}
});