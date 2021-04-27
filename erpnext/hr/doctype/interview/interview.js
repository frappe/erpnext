// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Interview', {
	onload: function (frm) {
		frm.events.set_job_applicant_query(frm);

		frm.set_query("interviewer", "interview_detail", function () {
			return {
				query: "erpnext.hr.doctype.interview.interview.get_interviewer_list"
			};
		});
	},

	refresh: function (frm) {
		if (frm.doc.docstatus == 1) {
			if (frm.doc.scheduled_on != frm.doc.original_date && frm.doc.status == "Scheduled") {
				frm.fields_dict.status.set_description(__("Interview was rescheduled from " + frm.doc.original_date + " to " + frm.doc.scheduled_on));
			}

			let now_date_time = frappe.datetime.now_datetime();
			if (now_date_time < frm.doc.scheduled_on && frm.doc.status === "Scheduled") {
				frm.add_custom_button(__("Reschedule Interview"), function () {
					frm.events.create_dialog(frm);
					frm.refresh();
				});
			} else if (frm.doc.status === "Scheduled") {
				frm.add_custom_button(__("End Session"), function () {
					frappe.db.set_value("Interview", frm.doc.name, "status", "In Review").then(() => {
						frappe.call({
							method: "erpnext.hr.interview.interview.send_review_reminder",
							args: {
								interview_name: frm.doc.name
							}
						})
						frm.refresh();
					});
				}).addClass("btn-primary");
			}
			if (frm.doc.status != "Completed") {
				let allowed_interviewers = [];
				frm.doc.interview_detail.forEach(values => {
					allowed_interviewers.push(values.interviewer);
				});
				if ((allowed_interviewers.includes(frappe.session.user)) && now_date_time > frm.doc.scheduled_on) {
					frm.add_custom_button(__("Submit Feedback"), function () {
						frappe.call({
							method: "erpnext.hr.doctype.interview.interview.get_expected_skill_set",
							args: {
								interview_round: frm.doc.interview_round
							},
							callback: function (r) {
								frm.events.create_feedback_dialog(frm, r.message);
								frm.refresh();
							}
						});
					});
				}
			}
		}
	},

	create_dialog: function (frm) {
		let d = new frappe.ui.Dialog({
			title: 'Reschedule Interview',
			fields: [{
				label: 'Schedule On',
				fieldname: 'scheduled_on',
				fieldtype: 'Datetime',
				reqd: 1
			}, ],
			primary_action_label: 'Reschedule',
			primary_action(values) {
				if (values.scheduled_on >= frappe.datetime.get_today()) {
					frm.events.reschedule_interview(frm, values.scheduled_on);
					frappe.msgprint(__("Interview Rescheduled"));
					frm.refresh();
					d.hide();
				} else {
					frappe.throw(__("You cannot schedule Interview for past date"));
				}
			}
		});
		d.show();
	},


	reschedule_interview: function (frm, scheduled_on) {
		frappe.call({
			method: "erpnext.hr.doctype.interview.interview.reschedule_interview",
			args: {
				name: frm.doc.name,
				scheduled_on: scheduled_on
			}
		});
	},

	create_feedback_dialog: function (frm, data) {
		let fields = frm.events.get_fields_for_feedback();

		let d = new frappe.ui.Dialog({
			title: __("Submit Feedback"),
			fields: [{
				fieldname: "skill_set",
				fieldtype: "Table",
				label: "Rate Based On Skill Set",
				cannot_add_rows: false,
				in_editable_grid: true,
				reqd: 1,
				fields: fields,
				data: data
			},
			{
				fieldname: "feedback",
				fieldtype: "Small Text",
				label: "Feedback"
			}
			],
			size: "large",
			primary_action: function (values) {
				frappe.call({
					method: 'erpnext.hr.doctype.interview.interview.create_interview_feedback',
					args: {
						data: values,
						interview_name: frm.doc.name,
						interviewer: frappe.session.user
					}
				});
				d.hide();
			}
		});
		d.show();
	},

	get_fields_for_feedback: function () {
		return [{
			fieldtype: 'Link',
			fieldname: "skill",
			options: 'Skill',
			in_list_view: 1,
			label: __('Skill')
		}, {
			fieldtype: 'Rating',
			fieldname: 'rating',
			label: __('Rating'),
			in_list_view: 1,
			reqd: 1,
		}];
	},

	set_job_applicant_query: function (frm) {
		frm.set_query('job_applicant', function () {
			let job_applicant_filters = {
				status: ["!=", "Rejected"]
			};
			if (frm.doc.designation) {
				job_applicant_filters.designation = frm.doc.designation;
			}
			return {
				filters: job_applicant_filters
			};
		});
	},

	interview_round: async function (frm) {
		frm.events.reset_values(frm);
		frm.set_value("job_applicant", '');

		let round_data = (await frappe.db.get_value('Interview Round', frm.doc.interview_round, 'designation')).message;
		frm.set_value("designation", round_data.designation);
		frm.events.set_job_applicant_query(frm);

		if (frm.doc.interview_round) {
			frm.events.set_interview_detail(frm);
		} else {
			frm.set_value("interview_detail", []);
		}
	},

	set_interview_detail: function (frm) {
		frappe.call({
			method: "erpnext.hr.doctype.interview.interview.get_interviewer",
			args: {
				interview_round: frm.doc.interview_round
			},
			callback: function (data) {
				let interview_detail = data.message;
				frm.set_value("interview_detail", []);
				if (data.message.length) {
					frm.set_value("interview_detail", interview_detail);
				}
			}
		});
	},

	job_applicant: function (frm) {
		if (!frm.doc.interview_round) {
			frm.doc.job_applicant = '';
			frm.refresh();
			frappe.throw(__("Select Interview Round First"));
		}

		if (frm.doc.job_applicant) {
			frm.events.set_designation_and_job_opening(frm);
		} else {
			frm.events.reset_values(frm);
		}
	},

	set_designation_and_job_opening: async function (frm) {
		let round_data = (await frappe.db.get_value('Interview Round', frm.doc.interview_round, 'designation')).message;
		frm.set_value("designation", round_data.designation);
		frm.events.set_job_applicant_query(frm);

		let job_applicant_data = (await frappe.db.get_value(
			'Job Applicant', frm.doc.job_applicant, ['designation', 'job_title', 'resume_link'],
		)).message;

		if (!round_data.designation) {
			frm.set_value("designation", job_applicant_data.designation);
		}

		frm.set_value("job_opening", job_applicant_data.job_title);
		frm.set_value("resume_link", job_applicant_data.resume_link);
	},

	reset_values: function (frm) {
		frm.set_value("designation", '');
		frm.set_value("job_opening", '');
		frm.set_value("resume_link", '');
	}
});
