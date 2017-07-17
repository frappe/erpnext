QUnit.module('setup');

QUnit.test('test student applicant', function(assert){
	assert.expect(23);
	let done = assert.async();
	let guradian_auto_code;
	let index;
	let guardian_name;
	frappe.run_serially([
		() => frappe.tests.setup_doctype('Academic Year'),
		() => frappe.tests.setup_doctype('Academic Term'),
		() => frappe.tests.setup_doctype('Program'),
		() => frappe.tests.setup_doctype('Student Admission'),

		// Setting up Guardian's entry and fetching its generated name
		() => frappe.tests.setup_doctype('Guardian'),
		() => {
			guradian_auto_code = $(location).attr('hash');
			index = guradian_auto_code.indexOf('GARD');
			guradian_auto_code = guradian_auto_code.substring(index);
			guardian_name = cur_frm.doc.guardian_name;
		},

		// Testing data entry for Student Applicant
		() => {
			return frappe.tests.make('Student Applicant',[
				{first_name: 'Test Fname'},
				{middle_name: 'Test Mname'},
				{last_name: 'Test Lname'},
				{program: 'Standard Test'},
				{student_admission: '2016-17 Admissions'},
				{date_of_birth: '1995-07-20'},
				{student_email_id: 'test@testmail.com'},
				{gender: 'Male'},
				{student_mobile_number: '9898980000'},
				{blood_group: 'O+'},
				{address_line_1: 'Test appt, Test Society,'},
				{address_line_2: 'Test district, Test city.'},
				{city: 'Test'},
				{state: 'Test'},
				{pincode: '395007'}
			]);
		},

		// Entry in Guardian child table
		() => $('a:contains("Guardian Details"):visible').click(),
		() => $('.btn:contains("Add Row"):visible').click(),
		() => {
			cur_frm.get_field("guardians").grid.grid_rows[0].doc.guardian = guradian_auto_code;
			cur_frm.get_field("guardians").grid.grid_rows[0].doc.relation = "Father";
			cur_frm.get_field("guardians").grid.grid_rows[0].doc.guardian_name = guardian_name;
		},
		// Entry in Sibling child table
		() => $('a:contains("Sibling Details"):visible').click(),
		() => $('.btn:contains("Add Row"):visible').click(),
		() => {
			cur_frm.get_field("siblings").grid.grid_rows[0].doc.full_name = "Test Name";
			cur_frm.get_field("siblings").grid.grid_rows[0].doc.gender = "Male";
			cur_frm.get_field("siblings").grid.grid_rows[0].doc.institution = "Test Institution";
			cur_frm.get_field("siblings").grid.grid_rows[0].doc.program = "Test Program";
			cur_frm.get_field("siblings").grid.grid_rows[0].doc.date_of_birth = "1995-07-20";
			$('span.hidden-xs.octicon.octicon-triangle-up').click();
			cur_frm.save();
		},
		() => {
			assert.ok(cur_frm.doc.first_name == 'Test Fname');
			assert.ok(cur_frm.doc.middle_name == 'Test Mname');
			assert.ok(cur_frm.doc.last_name == 'Test Lname');
			assert.ok(cur_frm.doc.program == 'Standard Test');
			assert.ok(cur_frm.doc.student_admission == '2016-17 Admissions');
			assert.ok(cur_frm.doc.date_of_birth == '1995-07-20');
			assert.ok(cur_frm.doc.student_email_id == 'test@testmail.com');
			assert.ok(cur_frm.doc.gender == 'Male');
			assert.ok(cur_frm.doc.student_mobile_number == '9898980000');
			assert.ok(cur_frm.doc.blood_group == 'O+');
			assert.ok(cur_frm.doc.address_line_1 == 'Test appt, Test Society,');
			assert.ok(cur_frm.doc.address_line_2 == 'Test district, Test city.');
			assert.ok(cur_frm.doc.city == 'Test');
			assert.ok(cur_frm.doc.state == 'Test');
			assert.ok(cur_frm.doc.pincode == '395007');
		},
		() => frappe.timeout(1),
		() => $('a:contains("Guardian Details"):visible').click(),
		() => $('.btn:contains("Add Row"):visible').click(),
		() => {
			assert.ok(cur_frm.get_field("guardians").grid.grid_rows[0].doc.guardian == guradian_auto_code);
			assert.ok(cur_frm.get_field("guardians").grid.grid_rows[0].doc.relation == 'Father');
			assert.ok(cur_frm.get_field("guardians").grid.grid_rows[0].doc.guardian_name == guardian_name);
		},
		() => $('a:contains("Sibling Details"):visible').click(),
		() => $('.btn:contains("Add Row"):visible').click(),
		() => {
			assert.ok(cur_frm.get_field("siblings").grid.grid_rows[0].doc.full_name == 'Test Name');
			assert.ok(cur_frm.get_field("siblings").grid.grid_rows[0].doc.gender == 'Male');
			assert.ok(cur_frm.get_field("siblings").grid.grid_rows[0].doc.institution == 'Test Institution');
			assert.ok(cur_frm.get_field("siblings").grid.grid_rows[0].doc.program == 'Test Program');
			assert.ok(cur_frm.get_field("siblings").grid.grid_rows[0].doc.date_of_birth == '1995-07-20');
		},
		() => done()
	]);
});