// Testing Student Module in Schools
QUnit.module('schools');

QUnit.test('Test: Student Group', function(assert){
	assert.expect(2);
	let done = assert.async();
	let instructor_code;
	let loop = ["test-batch-wise-group", "test-course-wise-group"];
	let tasks = [];

	frappe.run_serially([
		// Saving Instructor code beforehand
		() => frappe.set_route('List', 'Instructor'),
		() => frappe.timeout(0.5),
		() => frappe.tests.click_link('Instructor 1'),
		() => frappe.timeout(0.5),
		() => {instructor_code = frappe.get_route()[2];},

		// Creating a Batch and Course based group
		() => {
			loop.forEach(index => {
				tasks.push(() => {
					return frappe.tests.make('Student Group', [
						{academic_year: '2016-17'},
						{academic_term: '2016-17 (Semester 1)'},
						{program: "Standard Test"},
						{group_based_on: 'Batch'},
						{student_group_name: index},
						{max_strength: 10},
						{batch: 'A'},
						{instructors: [
							[
								{instructor: instructor_code}
							]
						]}
					]);
				});
			});
			return frappe.run_serially(tasks);
		},

		// Populating the created group with Students
		() => {
			tasks = [];
			loop.forEach(index => {
				tasks.push(
					() => frappe.timeout(0.3),
					() => frappe.set_route("Form", ('Student Group/' + index)),
					() => frappe.timeout(0.3),
					() => frappe.tests.click_button('Get Students'),
					() => frappe.timeout(0.2),
					() => {
						assert.equal(cur_frm.doc.students.length, 5, 'Successfully fetched list of students');
					},
				);
			});
			return frappe.run_serially(tasks);
		},

		() => done()
	]);
});