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

			if(frappe.model.can_read("Task")) {
				frm.add_custom_button(__("Gantt Chart"), function() {
					frappe.route_options = {"project": frm.doc.name};
					frappe.set_route("List", "Task", "Gantt");
				});
				
                frm.add_custom_button(__("Project Status Report"), function () {
                    frappe.set_route("List", "Project Status Report", {
                        project: frm.doc.name
                    });

                });

                frm.add_custom_button(__("Project Charter"), function () {
                    frappe.call({
			            "method": "existing_project_charter",
			            doc: cur_frm.doc,
			            callback: function(r) {
			            	frappe.set_route("Form", "Project Charter", r.message);
			            }
		        	});


	          		

                });
			}

			frm.trigger('show_dashboard');

			$('.layout-main-section .form-inner-toolbar :nth-child(3)').after('<hr style="border: solid 0.5px #ccc !important;margin:0 !important;"><p style="text-align: center;">Project Phase</p>');
			
		}



		frm.add_custom_button(__("Closure"), function () {
			frm.toggle_display("project_initiation", false);
            frm.toggle_display("customer_details", false);
            frm.toggle_display("project_financial_details", false);
            frm.toggle_display("planning", false);
            frm.toggle_display("communication_management_plan", false);
            frm.toggle_display("control", false);
            frm.toggle_display("section_break_5", false);
            frm.toggle_display("project_management_plan_section", false);
            frm.toggle_display("scope_of_work", false);
            frm.toggle_display("procurement_plan_section", false);
            frm.toggle_display("quality_management_plan", false);
            frm.toggle_display("risk_register_section", false);
            frm.toggle_display("responsibilities", false);
            frm.toggle_display("hd_cheanging_request", false);
            frm.toggle_display("project_issues_summary", false);
            frm.toggle_display("section_6", false);
            frm.toggle_display("section_7", false);
            frm.toggle_display("section_8", false);

            frm.toggle_display("closure", true);
            frm.toggle_display("project_information", true);
            frm.toggle_display("customer_decision", true);
            frm.toggle_display("approvals", true);

        });

		frm.add_custom_button(__("Controlling"), function () {
			frm.toggle_display("project_initiation", false);
            frm.toggle_display("customer_details", false);
            frm.toggle_display("project_financial_details", false);
            frm.toggle_display("planning", false);
            frm.toggle_display("communication_management_plan", false);
            frm.toggle_display("closure", false);
            frm.toggle_display("section_break_5", false);
            frm.toggle_display("project_management_plan_section", false);
            frm.toggle_display("scope_of_work", false);
            frm.toggle_display("procurement_plan_section", false);
            frm.toggle_display("quality_management_plan", false);
            frm.toggle_display("risk_register_section", false);
            frm.toggle_display("responsibilities", false);
            frm.toggle_display("project_information", false);
            frm.toggle_display("customer_decision", false);
            frm.toggle_display("approvals", false);
            frm.toggle_display("section_6", false);
            frm.toggle_display("section_7", false);
            frm.toggle_display("section_8", false);
            
            frm.toggle_display("control", true);
            frm.toggle_display("hd_cheanging_request", true);
            frm.toggle_display("project_issues_summary", true);

        });

        frm.add_custom_button(__("Planning"), function () {
            frm.toggle_display("project_initiation", false);
            frm.toggle_display("customer_details", false);
            frm.toggle_display("project_financial_details", false);
            frm.toggle_display("control", false);
            frm.toggle_display("closure", false);
            frm.toggle_display("section_break_5", false);
            frm.toggle_display("hd_cheanging_request", false);
            frm.toggle_display("project_issues_summary", false);
            frm.toggle_display("project_information", false);
            frm.toggle_display("customer_decision", false);
            frm.toggle_display("approvals", false);
            frm.toggle_display("section_6", false);
            frm.toggle_display("section_7", false);
            frm.toggle_display("section_8", false);

            frm.toggle_display("planning", true);
            frm.toggle_display("communication_management_plan", true);
            frm.toggle_display("project_management_plan_section", true);
            frm.toggle_display("scope_of_work", true);
            frm.toggle_display("procurement_plan_section", true);
            frm.toggle_display("quality_management_plan", true);
            frm.toggle_display("risk_register_section", true);
            frm.toggle_display("responsibilities", true);

        });

		frm.add_custom_button(__("Initiation"), function () {
			frm.toggle_display("planning", false);
            frm.toggle_display("communication_management_plan", false);
            frm.toggle_display("control", false);
            frm.toggle_display("closure", false);
            frm.toggle_display("project_management_plan_section", false);
            frm.toggle_display("scope_of_work", false);
            frm.toggle_display("procurement_plan_section", false);
            frm.toggle_display("quality_management_plan", false);
            frm.toggle_display("risk_register_section", false);
            frm.toggle_display("responsibilities", false);
            frm.toggle_display("hd_cheanging_request", false);
            frm.toggle_display("project_issues_summary", false);
            frm.toggle_display("project_information", false);
            frm.toggle_display("customer_decision", false);
            frm.toggle_display("approvals", false);

            frm.toggle_display("project_initiation", true);
            frm.toggle_display("customer_details", true);
            frm.toggle_display("project_financial_details", true);
            frm.toggle_display("section_break_5", true);
            frm.toggle_display("section_6", true);
            frm.toggle_display("section_7", true);
            frm.toggle_display("section_8", true);

        });



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
        billing_total += flt(d.total_billing_value);
    	});
    	frm.set_value("total_billing", billing_total);

        cost_value_total = 0;
        $.each(frm.doc.project_costing_schedule || [], function(i, d) {
            cost_value_total += flt(d.cost_value);
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


frappe.ui.form.on("Project Payment Schedule", "total_billing_value", function(frm, cdt, cdn) {
    // code for calculate total and set on parent field.
    billing_total = 0;
    $.each(frm.doc.project_payment_schedule || [], function(i, d) {
        billing_total += flt(d.total_billing_value);
    });
    frm.set_value("total_billing",billing_total);
});

frappe.ui.form.on("Project Costing Schedule", "cost_value", function(frm, cdt, cdn) {
    // code for calculate total and set on parent field.
    cost_value_total = 0;
    $.each(frm.doc.project_costing_schedule || [], function(i, d) {
        cost_value_total += flt(d.cost_value);
    });
    frm.set_value("total_cost_value",cost_value_total);
});


