// Testing Setup Module in Schools
QUnit.module('schools');

QUnit.test('Test: Student Group Creation Tool', function(assert){
	assert.expect(5);
	let done = assert.async();
	let instructor_code;
	let grid;
	let grid_row;
	frappe.run_serially([
		// Saving Instructor code beforehand
		() => frappe.set_route('List', 'Instructor'),
		() => frappe.timeout(0.5),
		() => {$('a:contains("Instructor 1"):visible').click();},
		() => frappe.timeout(0.5),
		() => {instructor_code = frappe.get_route()[2];},

		// Setting up the creation tool to generate and save Student Group
		() => frappe.set_route('Form', 'Student Group Creation Tool'),
		() => frappe.timeout(1),
		() => {
			cur_frm.set_value("academic_year", "2016-17");
			cur_frm.set_value("academic_term", "2016-17 (Semester 1)");
			cur_frm.set_value("program", "Standard Test");
			$(`.btn:contains("Get Courses"):visible`).click();
		},
		() => frappe.timeout(0.2),
		() => {
			assert.ok(cur_frm.get_field("courses").grid.grid_rows.length == 2, 'successfully created groups using the tool');
		},
		// Adjusting Name and Strength
		() => {
			(cur_frm.get_field("courses").grid).get_row(-1).toggle_view(true);
			cur_frm.doc.courses[1].max_strength = 10;
			cur_frm.doc.courses[1].student_group_name = "test-course-wise-group-2";
			$(`.octicon.octicon-triangle-up`).click();
			(cur_frm.get_field("courses").grid).get_row(0).toggle_view(true);
			cur_frm.doc.courses[0].max_strength = 10;
			cur_frm.doc.courses[0].student_group_name = "test-batch-wise-group-2";
			$(`.octicon.octicon-triangle-up`).click();

		},
		// Generating Student Group
		() => frappe.timeout(0.5),
		() => {$(`.btn:contains("Create Student Groups"):visible`).click();},
		() => frappe.timeout(0.5),
		() => {$(`.btn:contains("Close"):visible`).click();},
		() => frappe.timeout(0.5),
		() => {$(`.btn:contains("Close"):visible`).click();},

		// Goin to the generated group to set up student and instructor list
		() => frappe.set_route("List", 'Student Group'),
		() => frappe.timeout(0.3),
		() => {$('a:contains("batch-wise-group-2"):visible').click()},
		() => frappe.timeout(0.3),
		() => {$(`.btn:contains("Get Students"):visible`).click()},
		() => frappe.timeout(0.2),
		() => {
			assert.ok(cur_frm.get_field("students").grid.grid_rows.length == 1, 'Successfully fetched list of students');
		},
		() => frappe.timeout(0.5),
		() => {
			grid = cur_frm.get_field("instructors").grid;
			grid.add_new_row();
			grid_row = grid.get_row(-1).toggle_view(true);
			grid_row.doc.instructor = instructor_code;
			cur_frm.save();
		},
		() => {
			assert.ok(cur_frm.get_field("instructors").grid.grid_rows.length == 1, 'instrucor detail stored successfully');
		},

		// Goin to the generated group to set up student and instructor list
		() => frappe.set_route("List", 'Student Group'),
		() => frappe.timeout(0.3),
		() => {$('a:contains("course-wise-group-2"):visible').click()},
		() => frappe.timeout(0.3),
		() => {$(`.btn:contains("Get Students"):visible`).click()},
		() => frappe.timeout(0.2),
		() => {
			console.log(cur_frm.get_field("students").grid.grid_rows.length);
			assert.ok(cur_frm.get_field("students").grid.grid_rows.length == 1, 'Successfully fetched list of students');
		},
		() => {
			$(`.btn:contains("Add Row"):visible`)[1].click();
			(cur_frm.get_field("instructors").grid).get_row(0).toggle_view(true);
			cur_frm.doc.instructors[0].instructor = instructor_code;
			$(`.octicon.octicon-triangle-up`).click();
		},
		() => frappe.timeout(0.5),
		() => {
			grid = cur_frm.get_field("instructors").grid;
			grid.add_new_row();
			grid_row = grid.get_row(-1).toggle_view(true);
			grid_row.doc.instructor = instructor_code;
			cur_frm.save();
		},
		() => {
			assert.ok(cur_frm.get_field("instructors").grid.grid_rows.length == 1, 'instrucor detail stored successfully');
		},

		() => done()
	]);
});