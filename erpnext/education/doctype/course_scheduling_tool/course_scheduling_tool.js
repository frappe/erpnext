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
		frm.page.set_primary_action(__('Schedule Course'), () => {
			frm.call('schedule_course')
				.then(r => {
					if (!r.message) {
						frappe.throw(__('There were errors creating Course Schedule'));
					}
					const { course_schedules } = r.message;
					if (course_schedules) {
						const html = `
						<table class="table table-bordered">
							<caption>${__('Following course schedules were created')}</caption>
							<thead><tr><th>${__("Course")}</th><th>${__("Date")}</th></tr></thead>
							<tbody>
								${course_schedules.map(
									c => `<tr><td><a href="#Form/Course Schedule/${c.name}">${c.name}</a></td>
									<td>${c.schedule_date}</td></tr>`
								).join('')}
							</tbody>
						</table>`

						frappe.msgprint(html);
					}
				});
		});
	}
});