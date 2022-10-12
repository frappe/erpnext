// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt


frappe.ui.form.on('Course Scheduling Tool', {
	setup(frm) {
		frm.add_fetch('student_group', 'program', 'program');
		frm.add_fetch('student_group', 'course', 'course');
		frm.add_fetch('student_group', 'academic_year', 'academic_year');
		frm.add_fetch('student_group', 'academic_term', 'academic_term');
	},
	refresh(frm) {
		frm.disable_save();
		frm.trigger("render_days");
		frm.page.set_primary_action(__('Schedule Course'), () => {
			frappe.dom.freeze(__("Scheduling..."));
			frm.call('schedule_course', { days: frm.days.get_checked_options() })
				.then(r => {
					frappe.dom.unfreeze();
					if (!r.message) {
						frappe.throw(__('There were errors creating Course Schedule'));
					}
					const { course_schedules } = r.message;
					if (course_schedules) {
						const course_schedules_html = course_schedules.map(c => `
							<tr>
								<td><a href="/app/course-schedule/${c.name}">${c.name}</a></td>
								<td>${c.schedule_date}</td>
							</tr>
						`).join('');

						const html = `
							<table class="table table-bordered">
								<caption>${__('Following course schedules were created')}</caption>
								<thead><tr><th>${__("Course")}</th><th>${__("Date")}</th></tr></thead>
								<tbody>
									${course_schedules_html}
								</tbody>
							</table>
						`;

						frappe.msgprint(html);
					}
				});
		});
	},
	render_days: function(frm) {
		const days_html = $('<div class="days-editor">').appendTo(
			frm.fields_dict.days_html.wrapper
		);

		if (!frm.days) {
			frm.days = frappe.ui.form.make_control({
				parent: days_html,
				df: {
					fieldname: "days",
					fieldtype: "MultiCheck",
					select_all: true,
					columns: 4,
					options: [
						{
							label: __("Monday"),
							value: "Monday",
							checked: 0,
						},
						{
							label: __("Tuesday"),
							value: "Tuesday",
							checked: 0,
						},
						{
							label: __("Wednesday"),
							value: "Wednesday",
							checked: 0,
						},
						{
							label: __("Thursday"),
							value: "Thursday",
							checked: 0,
						},
						{
							label: __("Friday"),
							value: "Friday",
							checked: 0,
						},
						{
							label: __("Saturday"),
							value: "Saturday",
							checked: 0,
						},
						{
							label: __("Sunday"),
							value: "Sunday",
							checked: 0,
						},
					],
				},
				render_input: true,
			});
		}
	}
});
