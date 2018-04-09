// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Project", {
	onload: function(frm) {
		var so = frappe.meta.get_docfield("Project", "sales_order");
		// so.get_route_options_for_new_doc = function(field) {
		// 	if(frm.is_new()) return;
		// 	return {
		// 		"customer": frm.doc.customer,
		// 		"project_name": frm.doc.name
		// 	}
		// }

		frm.set_query('customer', 'erpnext.controllers.queries.customer_query');
		
		frm.set_query("user", "users", function() {
					return {
						query:"erpnext.projects.doctype.project.project.get_users_for_project"
					}
				});

		// sales order
		frm.set_query('sales_order', function() {
			var filters = {
				'project': ["in", frm.doc.__islocal ? [""] : [frm.doc.name, ""]]
			};

			if (frm.doc.customer) {
				filters["customer"] = frm.doc.customer;
			}

			return {
				filters: filters
			}
		});
	},
	project_sponsor : function (frm){
        if (cur_frm.doc.project_sponsor ){
        	frm.set_value("project_sponsor_ch", cur_frm.doc.project_sponsor );
        	frm.set_value("project_sponsor_name_ch", cur_frm.doc.project_sponsor_name );
        }
	},
	project_owner : function (frm){
        if (cur_frm.doc.project_owner ){
        	frm.set_value("project_owner_ch", cur_frm.doc.project_owner );
        	frm.set_value("project_owner_name_ch", cur_frm.doc.project_owner_name );
        }
	},
	project_manager : function (frm){
        if (cur_frm.doc.project_manager ){
        	frm.set_value("project_managr_ch", cur_frm.doc.project_manager );
        	frm.set_value("project_manager_name_ch", cur_frm.doc.project_manager_name );
        }
	},
	account : function (frm){
        if (cur_frm.doc.account ){
        	frm.set_value("account_ch", cur_frm.doc.account );
        }
	},
	customer : function (frm){
        if (cur_frm.doc.customer ){
        	frm.set_value("customer_ch", cur_frm.doc.customer );
        }
	},
	customer_project_manager : function (frm){
        if (cur_frm.doc.customer_project_manager ){
        	frm.set_value("customer_project_manager_ch", cur_frm.doc.customer_project_manager );
        }
	},
	customer_project_sponsor : function (frm){
        if (cur_frm.doc.customer_project_sponsor ){
        	frm.set_value("customer_project_sponsor_ch", cur_frm.doc.customer_project_sponsor );
        }
	},
    customer_project_owner : function (frm){
        if (cur_frm.doc.customer_project_owner ){
        	frm.set_value("customer_project_owner_ch", cur_frm.doc.customer_project_owner );
        }
	},
	po_number : function (frm){
        if (cur_frm.doc.po_number ){
        	frm.set_value("po_number_ch", cur_frm.doc.po_number );
        }
	},
	po_date : function (frm){
        if (cur_frm.doc.po_date ){
        	frm.set_value("po_date_ch", cur_frm.doc.po_date );
        }
	},
	customer_department : function (frm){
        if (cur_frm.doc.customer_department ){
        	frm.set_value("customer_department_ch", cur_frm.doc.customer_department );
        }
	},
	start_date : function (frm){
        if (cur_frm.doc.start_date ){
        	frm.set_value("expected_start_date", cur_frm.doc.start_date );
        }
	},
	end_date : function (frm){
        if (cur_frm.doc.end_date ){
        	frm.set_value("expected_end_date", cur_frm.doc.end_date );
        }
	},
    employee : function (frm){
        if (cur_frm.doc.employee ){
            frm.set_value("employee_ch", cur_frm.doc.employee );
        }
    },
    end_users : function (frm){
        if (cur_frm.doc.end_users ){
            frm.set_value("end_users_ch", cur_frm.doc.end_users );
        }
    },
    concerned_department : function (frm){
        if (cur_frm.doc.concerned_department ){
            frm.set_value("concerned_department_ch", cur_frm.doc.concerned_department );
        }
    },
	total_cost_price: function(frm) {

    	total_overall_profit = flt(cur_frm.doc.total_final_selling_price) - flt(cur_frm.doc.total_cost_price) ;
    	frm.set_value("overall_project_profit",total_overall_profit);

    	total_overall_markup = flt(cur_frm.doc.overall_project_profit) /flt(cur_frm.doc.total_cost_price) * 100;
    	frm.set_value("overall_project_markup",total_overall_markup);

        total_overall_margin= flt(cur_frm.doc.overall_project_profit) /flt(cur_frm.doc.total_final_selling_price) * 100;
    	frm.set_value("overall_project_margin",total_overall_margin);


	},
	total_final_selling_price: function(frm) {

    	total_overall_profit = flt(cur_frm.doc.total_final_selling_price) - flt(cur_frm.doc.total_cost_price) ;
    	frm.set_value("overall_project_profit",total_overall_profit);

    	total_overall_markup = flt(cur_frm.doc.overall_project_profit) /flt(cur_frm.doc.total_cost_price) * 100;
    	frm.set_value("overall_project_markup",total_overall_markup);

        total_overall_margin= flt(cur_frm.doc.overall_project_profit) /flt(cur_frm.doc.total_final_selling_price) * 100;
    	frm.set_value("overall_project_margin",total_overall_margin);


	},
	refresh: function(frm) {
		if(frm.doc.__islocal) {
			frm.web_link && frm.web_link.remove();
		} else {
			frm.add_web_link("/projects?project=" + encodeURIComponent(frm.doc.name));

			// if(frappe.model.can_read("Task")) {
			// 	frm.add_custom_button(__("Gantt Chart"), function() {
			// 		frappe.route_options = {"project": frm.doc.name};
			// 		frappe.set_route("List", "Task", "Gantt");
			// 	});
				
   //              frm.add_custom_button(__("Project Status Report"), function () {
   //                  frappe.set_route("List", "Project Status Report", {
   //                      project: frm.doc.name
   //                  });

   //              });

   //              frm.add_custom_button(__("Project Charter"), function () {
   //                  frappe.call({
			//             "method": "existing_project_charter",
			//             doc: cur_frm.doc,
			//             callback: function(r) {
			//             	frappe.set_route("Form", "Project Charter", r.message);
			//             }
		 //        	});

   //              });
			// }

			frm.trigger('show_dashboard');

			// $('.layout-main-section .form-inner-toolbar :nth-child(3)').after('<hr style="border: solid 0.5px #ccc !important;margin:0 !important;"><p style="text-align: center;">Project Phases</p>');
			// $('.layout-main-section-wrapper .layout-main-section .form-inner-toolbar').after('<style>.layout-main-section-wrapper .layout-main-section .form-inner-toolbar{height: 120px !important;}</style>');
			// $('.layout-main-section-wrapper .layout-main-section .form-inner-toolbar').after('<style>.layout-main-section-wrapper .layout-main-section .form-inner-toolbar button:nth-child(n+4){float: left !important;}</style>');


		}



        frm.add_custom_button(__("Project Initiation"), function () {
			frm.toggle_display("planning", false);
            frm.toggle_display("communication_management_plan", false);
            frm.toggle_display("control", false);
            frm.toggle_display("closure", false);
            frm.toggle_display("project_management_plan_section", false);
            frm.toggle_display("scope_of_work", false);
            frm.toggle_display("quality_management_plan", false);
            frm.toggle_display("risk_register_section", false);
            frm.toggle_display("responsibilities", false);
            frm.toggle_display("hd_cheanging_request", false);
            frm.toggle_display("project_issues_summary", false);
            frm.toggle_display("project_information", false);
            frm.toggle_display("customer_decision", false);
            frm.toggle_display("approvals", false);
            frm.toggle_display("section_break_133", false);
            frm.toggle_display("section_break_165", false);
            frm.toggle_display("section_break_268", false);
            frm.toggle_display("previous_project_schedules", false);

            frm.toggle_display("project_initiation", true);
            frm.toggle_display("customer_details", true);
            frm.toggle_display("section_6", true);
            frm.toggle_display("section_7", true);
            frm.toggle_display("section_8", true);
            frm.toggle_display("charter", true);
            frm.toggle_display("section_break_1", true);

        });

        frm.add_custom_button(__("Project Planning"), function () {
            frm.toggle_display("project_initiation", false);
            frm.toggle_display("customer_details", false);
            frm.toggle_display("control", false);
            frm.toggle_display("closure", false);
            frm.toggle_display("hd_cheanging_request", false);
            frm.toggle_display("project_issues_summary", false);
            frm.toggle_display("project_information", false);
            frm.toggle_display("customer_decision", false);
            frm.toggle_display("approvals", false);
            frm.toggle_display("section_6", false);
            frm.toggle_display("section_7", false);
            frm.toggle_display("section_8", false);
            frm.toggle_display("charter", false);
            frm.toggle_display("section_break_1", false);
            frm.toggle_display("section_break_165", false);
            frm.toggle_display("previous_project_schedules", false);

            frm.toggle_display("planning", true);
            frm.toggle_display("communication_management_plan", true);
            frm.toggle_display("project_management_plan_section", true);
            frm.toggle_display("scope_of_work", true);
            frm.toggle_display("quality_management_plan", true);
            frm.toggle_display("risk_register_section", true);
            frm.toggle_display("responsibilities", true);
            frm.toggle_display("section_break_133", true);
            frm.toggle_display("section_break_268", true);

        });

        frm.add_custom_button(__("Project Implementation, Monitoring and Controlling"), function () {
			frm.toggle_display("project_initiation", false);
            frm.toggle_display("customer_details", false);
            frm.toggle_display("planning", false);
            frm.toggle_display("communication_management_plan", false);
            frm.toggle_display("closure", false);
            frm.toggle_display("project_management_plan_section", false);
            frm.toggle_display("scope_of_work", false);
            frm.toggle_display("quality_management_plan", false);
            frm.toggle_display("risk_register_section", false);
            frm.toggle_display("responsibilities", false);
            frm.toggle_display("project_information", false);
            frm.toggle_display("customer_decision", false);
            frm.toggle_display("approvals", false);
            frm.toggle_display("section_6", false);
            frm.toggle_display("section_7", false);
            frm.toggle_display("section_8", false);
            frm.toggle_display("charter", false);
            frm.toggle_display("section_break_1", false);
            frm.toggle_display("section_break_133", false);
            frm.toggle_display("section_break_268", false);
            
            frm.toggle_display("control", true);
            frm.toggle_display("hd_cheanging_request", true);
            frm.toggle_display("project_issues_summary", true);
            frm.toggle_display("section_break_165", true);
            frm.toggle_display("previous_project_schedules", true);

        });

        frm.add_custom_button(__("Project Closure"), function () {
			frm.toggle_display("project_initiation", false);
            frm.toggle_display("customer_details", false);
            frm.toggle_display("planning", false);
            frm.toggle_display("communication_management_plan", false);
            frm.toggle_display("control", false);
            frm.toggle_display("project_management_plan_section", false);
            frm.toggle_display("scope_of_work", false);
            frm.toggle_display("quality_management_plan", false);
            frm.toggle_display("risk_register_section", false);
            frm.toggle_display("responsibilities", false);
            frm.toggle_display("hd_cheanging_request", false);
            frm.toggle_display("project_issues_summary", false);
            frm.toggle_display("section_6", false);
            frm.toggle_display("section_7", false);
            frm.toggle_display("section_8", false);
            frm.toggle_display("charter", false);
            frm.toggle_display("section_break_1", false);
            frm.toggle_display("section_break_133", false);
            frm.toggle_display("section_break_165", false);
            frm.toggle_display("section_break_268", false);
            frm.toggle_display("previous_project_schedules", false);

            frm.toggle_display("closure", true);
            frm.toggle_display("project_information", true);
            frm.toggle_display("customer_decision", true);
            frm.toggle_display("approvals", true);

        });


			$('.layout-main-section .form-inner-toolbar :nth-child(1)').before('<b><p style="text-align: center;font-size: 25px;">Project Phases</p></b>');
			$('.layout-main-section-wrapper .layout-main-section .form-inner-toolbar').after('<style>.layout-main-section-wrapper .layout-main-section .form-inner-toolbar{height: 100px !important;}</style>');
			$('.layout-main-section-wrapper .layout-main-section .form-inner-toolbar').after('<style>.layout-main-section-wrapper .layout-main-section .form-inner-toolbar button:nth-child(n+1){float: left !important;}</style>');


	},
	tasks_refresh: function(frm) {
		var grid = frm.get_field('tasks').grid;
		grid.wrapper.find('select[data-fieldname="status"]').each(function() {
			if($(this).val()==='Open') {
				$(this).addClass('input-indicator-open');
			} else {
				$(this).removeClass('input-indicator-open');
			}
		});
	},
	show_dashboard: function(frm) {
		if(frm.doc.__onload.activity_summary.length) {
			var hours = $.map(frm.doc.__onload.activity_summary, function(d) { return d.total_hours });
			var max_count = Math.max.apply(null, hours);
			var sum = hours.reduce(function(a, b) { return a + b; }, 0);
			var section = frm.dashboard.add_section(
				frappe.render_template('project_dashboard',
					{
						data: frm.doc.__onload.activity_summary,
						max_count: max_count,
						sum: sum
					}));

			section.on('click', '.time-sheet-link', function() {
				var activity_type = $(this).attr('data-activity_type');
				frappe.set_route('List', 'Timesheet',
					{'activity_type': activity_type, 'project': frm.doc.name, 'status': ["!=", "Cancelled"]});
			});
		}
	},
	validate: function(frm){
		grand_total = 0;
	    $.each(frm.doc.project_financial_detail || [], function(i, d) {
	        grand_total += flt(d.cost_price);
	    });
	    frm.set_value("total_cost_price", grand_total);

	    total = 0;
        $.each(frm.doc.project_financial_detail || [], function(i, d) {
        	total += flt(d.final_selling_price);
        });
    	frm.set_value("total_final_selling_price", total);

    	total_overall_profit = flt(cur_frm.doc.total_final_selling_price) - flt(cur_frm.doc.total_cost_price) ;
    	frm.set_value("overall_project_profit",total_overall_profit);

    	total_overall_markup = flt(cur_frm.doc.overall_project_profit) /flt(cur_frm.doc.total_cost_price) * 100;
    	frm.set_value("overall_project_markup",total_overall_markup);

        total_overall_margin= flt(cur_frm.doc.overall_project_profit) /flt(cur_frm.doc.total_final_selling_price) * 100;
    	frm.set_value("overall_project_margin",total_overall_margin);

    	billing_total = 0;
    	$.each(frm.doc.project_payment_schedule || [], function(i, d) {
        billing_total += flt(d.items_value);
    	});
    	frm.set_value("total_billing", billing_total);

        cost_value_total = 0;
        $.each(frm.doc.project_costing_schedule || [], function(i, d) {
            cost_value_total += flt(d.items_cost_price);
        });
        frm.set_value("total_cost_value",cost_value_total);
	}

});

frappe.ui.form.on("Project Task", {
	edit_task: function(frm, doctype, name) {
		var doc = frappe.get_doc(doctype, name);
		if(doc.task_id) {
			frappe.set_route("Form", "Task", doc.task_id);
		} else {
			msgprint(__("Save the document first."));
		}
	},
	status: function(frm, doctype, name) {
		frm.trigger('tasks_refresh');
	},
});


frappe.ui.form.on("Roles And Responsibilities", {
	party: function(frm, doctype, name) {

		frm.set_value("client_steering_name", );
		frm.set_value("client_ownership_name", );
		frm.set_value("client_management_name", );
		frm.set_value("client_technical_name", );
		frm.set_value("tawari_steering_name", );
		frm.set_value("tawari_ownership_name", );
		frm.set_value("tawari_management_name", );
		frm.set_value("tawari_technical_name", );
		frm.set_value("partner_steering_name", );
		frm.set_value("partner_ownership_name", );
		frm.set_value("partner_management_name", );
		frm.set_value("partner_technical_name", );
		
		for(var i =0;i<cur_frm.doc.roles_and_responsibilities.length;i++){
			if(cur_frm.doc.roles_and_responsibilities[i].party == 'Client'){
	            if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Steering Committee'){
	                frm.set_value("client_steering_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Ownership level'){
	                frm.set_value("client_ownership_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Project Management'){
	                frm.set_value("client_management_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Technical management'){
	                frm.set_value("client_technical_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }
	        }
	        if(cur_frm.doc.roles_and_responsibilities[i].party == 'Tawari'){
	            if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Steering Committee'){
	                frm.set_value("tawari_steering_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Ownership level'){
	                frm.set_value("tawari_ownership_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Project Management'){
	                frm.set_value("tawari_management_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Technical management'){
	                frm.set_value("tawari_technical_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }
	        }
	        if(cur_frm.doc.roles_and_responsibilities[i].party == 'Partner/Supplier'){
	            if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Steering Committee'){
	                frm.set_value("partner_steering_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Ownership level'){
	                frm.set_value("partner_ownership_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Project Management'){
	                frm.set_value("partner_management_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Technical management'){
	                frm.set_value("partner_technical_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }
	        }
	    }

	},
	project_role: function(frm, doctype, name) {
		
		frm.set_value("client_steering_name", );
		frm.set_value("client_ownership_name", );
		frm.set_value("client_management_name", );
		frm.set_value("client_technical_name", );
		frm.set_value("tawari_steering_name", );
		frm.set_value("tawari_ownership_name", );
		frm.set_value("tawari_management_name", );
		frm.set_value("tawari_technical_name", );
		frm.set_value("partner_steering_name", );
		frm.set_value("partner_ownership_name", );
		frm.set_value("partner_management_name", );
		frm.set_value("partner_technical_name", );
		
		for(var i =0;i<cur_frm.doc.roles_and_responsibilities.length;i++){
			if(cur_frm.doc.roles_and_responsibilities[i].party == 'Client'){
	            if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Steering Committee'){
	                frm.set_value("client_steering_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Ownership level'){
	                frm.set_value("client_ownership_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Project Management'){
	                frm.set_value("client_management_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Technical management'){
	                frm.set_value("client_technical_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }
	        }
	        if(cur_frm.doc.roles_and_responsibilities[i].party == 'Tawari'){
	            if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Steering Committee'){
	                frm.set_value("tawari_steering_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Ownership level'){
	                frm.set_value("tawari_ownership_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Project Management'){
	                frm.set_value("tawari_management_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Technical management'){
	                frm.set_value("tawari_technical_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }
	        }
	        if(cur_frm.doc.roles_and_responsibilities[i].party == 'Partner/Supplier'){
	            if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Steering Committee'){
	                frm.set_value("partner_steering_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Ownership level'){
	                frm.set_value("partner_ownership_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Project Management'){
	                frm.set_value("partner_management_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Technical management'){
	                frm.set_value("partner_technical_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }
	        }
	    }

	},
	name1: function(frm, doctype, name) {

		frm.set_value("client_steering_name", );
		frm.set_value("client_ownership_name", );
		frm.set_value("client_management_name", );
		frm.set_value("client_technical_name", );
		frm.set_value("tawari_steering_name", );
		frm.set_value("tawari_ownership_name", );
		frm.set_value("tawari_management_name", );
		frm.set_value("tawari_technical_name", );
		frm.set_value("partner_steering_name", );
		frm.set_value("partner_ownership_name", );
		frm.set_value("partner_management_name", );
		frm.set_value("partner_technical_name", );
		
		for(var i =0;i<cur_frm.doc.roles_and_responsibilities.length;i++){
			if(cur_frm.doc.roles_and_responsibilities[i].party == 'Client'){
	            if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Steering Committee'){
	                frm.set_value("client_steering_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Ownership level'){
	                frm.set_value("client_ownership_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Project Management'){
	                frm.set_value("client_management_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Technical management'){
	                frm.set_value("client_technical_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }
	        }
	        if(cur_frm.doc.roles_and_responsibilities[i].party == 'Tawari'){
	            if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Steering Committee'){
	                frm.set_value("tawari_steering_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Ownership level'){
	                frm.set_value("tawari_ownership_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Project Management'){
	                frm.set_value("tawari_management_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Technical management'){
	                frm.set_value("tawari_technical_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }
	        }
	        if(cur_frm.doc.roles_and_responsibilities[i].party == 'Partner/Supplier'){
	            if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Steering Committee'){
	                frm.set_value("partner_steering_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Ownership level'){
	                frm.set_value("partner_ownership_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Project Management'){
	                frm.set_value("partner_management_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }if(cur_frm.doc.roles_and_responsibilities[i].project_role == 'Technical management'){
	                frm.set_value("partner_technical_name", cur_frm.doc.roles_and_responsibilities[i].name1);
	            }
	        }
	    }

	}
	
});




frappe.listview_settings['Project'] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		return [__(doc.status), {
			"Started": "green",
			"Ongoing": "orange",
			"Cancelled": "red",
			"On hold": "orange",
			"Completed": "green",
			"Open": "green",
			"Pending PO": "green"
		}[doc.status], "status,=," + doc.status];
	}
};


frappe.ui.form.on("Project Financial Details", "cost_price", function(frm, cdt, cdn) {
    // code for calculate total and set on parent field.
    grand_total = 0;
    $.each(frm.doc.project_financial_detail || [], function(i, d) {
        grand_total += flt(d.cost_price);
    });
    frm.set_value("total_cost_price", grand_total);
});


frappe.ui.form.on("Project Financial Details", "final_selling_price", function(frm, cdt, cdn) {
    // code for calculate total and set on parent field.
    total = 0;
    $.each(frm.doc.project_financial_detail || [], function(i, d) {
        total += flt(d.final_selling_price);
    });
    frm.set_value("total_final_selling_price", total);
});


frappe.ui.form.on("Project Payment Schedule", "items_value", function(frm, cdt, cdn) {
    // code for calculate total and set on parent field.
    billing_total = 0;
    $.each(frm.doc.project_payment_schedule || [], function(i, d) {
        billing_total += flt(d.items_value);
    });
    frm.set_value("total_billing",billing_total);
});

frappe.ui.form.on("Project Costing Schedule", "cost_value", function(frm, cdt, cdn) {
    // code for calculate total and set on parent field.
    cost_value_total = 0;
    $.each(frm.doc.project_costing_schedule || [], function(i, d) {
        cost_value_total += flt(d.items_cost_price);
    });
    frm.set_value("total_cost_value",cost_value_total);
});



frappe.ui.form.on('Project Financial Details', {
    selling_price: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if(row.selling_price || row.additions_value){
			frappe.model.set_value(cdt, cdn, "final_selling_price", row.selling_price + row.additions_value);

		}

    },
    additions_value: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if(row.selling_price || row.additions_value){
			frappe.model.set_value(cdt, cdn, "final_selling_price", row.selling_price + row.additions_value);

		}

    }


})


cur_frm.set_query("scope_item", "project_payment_schedule", function(doc, cdt, cdn) {
			var row = locals[cdt][cdn];
	        item_length = cur_frm.doc.project_financial_detail.length
	        item = []
	        cost = []
	        for(var i = 0; i < item_length; i++){
	        	item.push(cur_frm.doc.project_financial_detail[i].scope_item)
	        	cost.push(cur_frm.doc.project_financial_detail[i].final_selling_price)
	        }
	        // console.log(item)
	        // console.log(cost)
			var d = locals[cdt][cdn];
			return{
				filters: [
					['Item', 'name', 'in', item]
				]
			}
		});



frappe.ui.form.on('Project Payment Schedule', {
	scope_item: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];

        item_length = cur_frm.doc.project_financial_detail.length
        item = []
        cost = []
        for(var i = 0; i < item_length; i++){
        	item.push(cur_frm.doc.project_financial_detail[i].scope_item)
        	cost.push(cur_frm.doc.project_financial_detail[i].final_selling_price)
        }
        frappe.model.set_value(cdt, cdn, "items_value", cost[item.indexOf(row.scope_item)]);

    },
    items_value: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if(row.items_value && row.billing_percentage){
			frappe.model.set_value(cdt, cdn, "billing_value", row.billing_percentage/100 * row.items_value);

		}

    },
    billing_percentage: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if(row.items_value && row.billing_percentage){
			frappe.model.set_value(cdt, cdn, "billing_value", row.billing_percentage/100 * row.items_value);

		}

    }


})



cur_frm.set_query("scope_item", "project_costing_schedule", function(doc, cdt, cdn) {
			var row = locals[cdt][cdn];
	        item_length = cur_frm.doc.project_financial_detail.length
	        item = []
	        cost = []
	        for(var i = 0; i < item_length; i++){
	        	item.push(cur_frm.doc.project_financial_detail[i].scope_item)
	        	cost.push(cur_frm.doc.project_financial_detail[i].final_selling_price)
	        }
	        // console.log(item)
	        // console.log(cost)
			var d = locals[cdt][cdn];
			return{
				filters: [
					['Item', 'name', 'in', item]
				]
			}
		});


frappe.ui.form.on('Project Costing Schedule', {
	scope_item: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];

        item_length = cur_frm.doc.project_financial_detail.length
        item = []
        cost = []
        for(var i = 0; i < item_length; i++){
        	item.push(cur_frm.doc.project_financial_detail[i].scope_item)
        	cost.push(cur_frm.doc.project_financial_detail[i].cost_price)
        }
        frappe.model.set_value(cdt, cdn, "items_cost_price", cost[item.indexOf(row.scope_item)]);

    },
    items_cost_price: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if(row.items_cost_price && row.cost_value_percentage){
			frappe.model.set_value(cdt, cdn, "cost_value", row.cost_value_percentage/100 * row.items_cost_price);

		}

    },
    cost_value_percentage: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if(row.items_cost_price && row.cost_value_percentage){
			frappe.model.set_value(cdt, cdn, "cost_value", row.cost_value_percentage/100 * row.items_cost_price);

		}

    }

})