// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// For license information, please see license.txt

// for communication
cur_frm.email_field = "email_id";

frappe.ui.form.on("Job Applicant", {
	refresh: function(frm) {
		frm.set_query("job_title", function() {
			return {
				filters: {
					'status': 'Open'
				}
			};
		});
		frm.events.create_custom_buttons(frm);
		frm.events.make_dashboard(frm);
	},

	create_custom_buttons: function(frm) {
		if (!frm.doc.__islocal && frm.doc.status !== "Rejected" && frm.doc.status !== "Accepted") {
			frm.add_custom_button(__("Create Interview"), function() {
				frm.events.create_dialog(frm);
			});
		}

		if (!frm.doc.__islocal) {
			if (frm.doc.__onload && frm.doc.__onload.job_offer) {
				$('[data-doctype="Employee Onboarding"]').find("button").show();
				$('[data-doctype="Job Offer"]').find("button").hide();
				frm.add_custom_button(__("Job Offer"), function() {
					frappe.set_route("Form", "Job Offer", frm.doc.__onload.job_offer);
				}, __("View"));
			} else {
				$('[data-doctype="Employee Onboarding"]').find("button").hide();
				$('[data-doctype="Job Offer"]').find("button").show();
				frm.add_custom_button(__("Job Offer"), function() {
					frappe.route_options = {
						"job_applicant": frm.doc.name,
						"applicant_name": frm.doc.applicant_name,
						"designation": frm.doc.job_opening,
					};
					frappe.new_doc("Job Offer");
				});
			}
		}
	},

	make_dashboard: function(frm) {
		frappe.call({
			method: "erpnext.hr.doctype.job_applicant.job_applicant.get_interview_details",
			args: {
				job_applicant: frm.doc.name
			},
			callback: function(r) {
				$("div").remove(".form-dashboard-section.custom");
				frm.dashboard.add_section(
					frappe.render_template('job_applicant_dashboard', {
						data: r.message
					}),
					__("Interview Summary")
				);
			}
		});
	},

	create_dialog: function(frm) {
		let d = new frappe.ui.Dialog({
			title: 'Enter Interview Round',
			fields: [
				{
					label: 'Interview Round',
					fieldname: 'interview_round',
					fieldtype: 'Link',
					options: 'Interview Round'
				},
			],
			primary_action_label: 'Create Interview',
			primary_action(values) {
				frm.events.create_interview(frm, values);
				d.hide();
			}
		});
		d.show();
	},

	create_interview: function (frm, values) {
		frappe.call({
			method: "erpnext.hr.doctype.job_applicant.job_applicant.create_interview",
			args: {
				doc: frm.doc,
				interview_round: values.interview_round
			},
			callback: function (r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	}
});
