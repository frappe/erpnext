// Testing Student Module in Schools
QUnit.module('schools');

QUnit.test('Test: Student Group', function(assert){
	assert.expect(2);
	let done = assert.async();
	let instructor_code;
	let group_based_on = ["test-batch-wise-group", "test-course-wise-group"];
	let tasks = [];

	frappe.run_serially([
		// Saving Instructor code beforehand
		() => frappe.db.get_value('Instructor', {'instructor_name': 'Instructor 1'}, 'name'),
		(instructor) => {instructor_code = instructor.message.name;},

		// Creating a Batch and Course based group
		() => {
			return frappe.tests.make('Student Group', [
				{academic_year: '2016-17'},
				{academic_term: '2016-17 (Semester 1)'},
				{program: "Standard Test"},
				{group_based_on: 'Batch'},
				{student_group_name: group_based_on[0]},
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
				{student_group_name: group_based_on[1]},
				{max_strength: 10},
				{batch: 'A'},
				{course: 'Test_Sub'},
				{instructors: [
					[
						{instructor: instructor_code}
					]
				]}
			]);
		},

		// Populating the created group with Students
		() => {
			tasks = [];
			group_based_on.forEach(index => {
				tasks.push(
					() => frappe.timeout(0.5),
					() => frappe.set_route("Form", ('Student Group/' + index)),
					() => frappe.timeout(0.5),
					() => frappe.tests.click_button('Get Students'),
					() => frappe.timeout(0.5),
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