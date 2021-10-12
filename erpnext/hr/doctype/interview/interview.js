// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Interview', {
	onload: function (frm) {
		frm.events.set_job_applicant_query(frm);

		frm.set_query('interviewer', 'interview_details', function () {
			return {
				query: 'erpnext.hr.doctype.interview.interview.get_interviewer_list'
			};
		});
	},

	refresh: function (frm) {
		if (frm.doc.docstatus != 2 && !frm.doc.__islocal) {
			if (frm.doc.status === 'Pending') {
				frm.add_custom_button(__('Reschedule Interview'), function() {
					frm.events.show_reschedule_dialog(frm);
					frm.refresh();
				});
			}

			let allowed_interviewers = [];
			frm.doc.interview_details.forEach(values => {
				allowed_interviewers.push(values.interviewer);
			});

			if ((allowed_interviewers.includes(frappe.session.user))) {
				frappe.db.get_value('Interview Feedback', {'interviewer': frappe.session.user, 'interview': frm.doc.name, 'docstatus': 1}, 'name', (r) => {
					if (Object.keys(r).length === 0) {
						frm.add_custom_button(__('Submit Feedback'), function () {
							frappe.call({
								method: 'erpnext.hr.doctype.interview.interview.get_expected_skill_set',
								args: {
									interview_round: frm.doc.interview_round
								},
								callback: function (r) {
									frm.events.show_feedback_dialog(frm, r.message);
									frm.refresh();
								}
							});
						}).addClass('btn-primary');
					}
				});
			}
		}
	},

	show_reschedule_dialog: function (frm) {
		let d = new frappe.ui.Dialog({
			title: 'Reschedule Interview',
			fields: [
				{
					label: 'Schedule On',
					fieldname: 'scheduled_on',
					fieldtype: 'Date',
					reqd: 1
				},
				{
					label: 'From Time',
					fieldname: 'from_time',
					fieldtype: 'Time',
					reqd: 1
				},
				{
					label: 'To Time',
					fieldname: 'to_time',
					fieldtype: 'Time',
					reqd: 1
				}
			],
			primary_action_label: 'Reschedule',
			primary_action(values) {
				frm.call({
					method: 'reschedule_interview',
					doc: frm.doc,
					args: {
						scheduled_on: values.scheduled_on,
						from_time: values.from_time,
						to_time: values.to_time
					}
				}).then(() => {
					frm.refresh();
					d.hide();
				});
			}
		});
		d.show();
	},

	show_feedback_dialog: function (frm, data) {
		let fields = frm.events.get_fields_for_feedback();

		let d = new frappe.ui.Dialog({
			title: __('Submit Feedback'),
			fields: [
				{
					fieldname: 'skill_set',
					fieldtype: 'Table',
					label: __('Skill Assessment'),
					cannot_add_rows: false,
					in_editable_grid: true,
					reqd: 1,
					fields: fields,
					data: data
				},
				{
					fieldname: 'result',
					fieldtype: 'Select',
					options: ['', 'Cleared', 'Rejected'],
					label: __('Result')
				},
				{
					fieldname: 'feedback',
					fieldtype: 'Small Text',
					label: __('Feedback')
				}
			],
			size: 'large',
			minimizable: true,
			primary_action: function(values) {
				frappe.call({
					method: 'erpnext.hr.doctype.interview.interview.create_interview_feedback',
					args: {
						data: values,
						interview_name: frm.doc.name,
						interviewer: frappe.session.user,
						job_applicant: frm.doc.job_applicant
					}
				}).then(() => {
					frm.refresh();
				});
				d.hide();
			}
		});
		d.show();
	},

	get_fields_for_feedback: function () {
		return [{
			fieldtype: 'Link',
			fieldname: 'skill',
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
				status: ['!=', 'Rejected']
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
		frm.set_value('job_applicant', '');

		let round_data = (await frappe.db.get_value('Interview Round', frm.doc.interview_round, 'designation')).message;
		frm.set_value('designation', round_data.designation);
		frm.events.set_job_applicant_query(frm);

		if (frm.doc.interview_round) {
			frm.events.set_interview_details(frm);
		} else {
			frm.set_value('interview_details', []);
		}
	},

	set_interview_details: function (frm) {
		frappe.call({
			method: 'erpnext.hr.doctype.interview.interview.get_interviewers',
			args: {
				interview_round: frm.doc.interview_round
			},
			callback: function (data) {
				let interview_details = data.message;
				frm.set_value('interview_details', []);
				if (data.message.length) {
					frm.set_value('interview_details', interview_details);
				}
			}
		});
	},

	job_applicant: function (frm) {
		if (!frm.doc.interview_round) {
			frm.doc.job_applicant = '';
			frm.refresh();
			frappe.throw(__('Select Interview Round First'));
		}

		if (frm.doc.job_applicant) {
			frm.events.set_designation_and_job_opening(frm);
		} else {
			frm.events.reset_values(frm);
		}
	},

	set_designation_and_job_opening: async function (frm) {
		let round_data = (await frappe.db.get_value('Interview Round', frm.doc.interview_round, 'designation')).message;
		frm.set_value('designation', round_data.designation);
		frm.events.set_job_applicant_query(frm);

		let job_applicant_data = (await frappe.db.get_value(
			'Job Applicant', frm.doc.job_applicant, ['designation', 'job_title', 'resume_link'],
		)).message;

		if (!round_data.designation) {
			frm.set_value('designation', job_applicant_data.designation);
		}

		frm.set_value('job_opening', job_applicant_data.job_title);
		frm.set_value('resume_link', job_applicant_data.resume_link);
	},

	reset_values: function (frm) {
		frm.set_value('designation', '');
		frm.set_value('job_opening', '');
		frm.set_value('resume_link', '');
	}
});
