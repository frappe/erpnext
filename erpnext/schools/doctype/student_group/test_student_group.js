// Testing Student Module in Schools
QUnit.module('schools');

QUnit.test('Test: Student Group', function(assert){
	assert.expect(2);
	let done = assert.async();
	let instructor_code;

	frappe.run_serially([
		// Saving Instructor code beforehand
		() => frappe.set_route('List', 'Instructor'),
		() => frappe.timeout(0.5),
		() => {$('a:contains("Instructor 1"):visible').click();},
		() => frappe.timeout(0.5),
		() => {instructor_code = frappe.get_route()[2];},

		() => {
			return frappe.tests.make('Student Group', [
				{academic_year: '2016-17'},
				{academic_term: '2016-17 (Semester 1)'},
				{program: "Standard Test"},
				{group_based_on: 'Batch'},
				{student_group_name: "test-batch-wise-group"},
				{max_strength: 10},
				{batch: 'A'},
				{instructors: [
					[
						{instructor: instructor_code}
					]
				]}
			]);
		},
		() => {
			return frappe.tests.make('Student Group', [
				{academic_year: '2016-17'},
				{academic_term: '2016-17 (Semester 1)'},
				{program: "Standard Test"},
				{group_based_on: 'Course'},
				{course: 'Test_Sub'},
				{student_group_name: "test-course-wise-group"},
				{max_strength: 10},
				{batch: 'A'},
				{instructors: [
					[
						{instructor: instructor_code}
					]
				]}
			]);
		},
		() => frappe.set_route("List", 'Student Group'),
		() => frappe.timeout(0.3),
		() => {$('a:contains("batch-wise-group"):visible').click()},
		() => frappe.timeout(0.3),
		() => {$(`.btn:contains("Get Students"):visible`).click()},
		() => frappe.timeout(0.2),
		() => {
			console.log(cur_frm.get_field("students").grid.grid_rows.length);
			assert.ok(cur_frm.get_field("students").grid.grid_rows.length == 1, 'Successfully fetched list of students');
		},
		() => frappe.set_route("List", 'Student Group'),
		() => frappe.timeout(0.3),
		() => {$('a:contains("course-wise-group"):visible').click()},
		() => frappe.timeout(0.3),
		() => {$(`.btn:contains("Get Students"):visible`).click()},
		() => frappe.timeout(0.2),
		() => {
			console.log(cur_frm.get_field("students").grid.grid_rows.length);
			assert.ok(cur_frm.get_field("students").grid.grid_rows.length == 1, 'Successfully fetched list of students');
		},
		() => done()
	]);
});