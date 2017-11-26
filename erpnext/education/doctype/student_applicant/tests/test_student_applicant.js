// Testing Admission module in Education
QUnit.module('education');

QUnit.test('Test: Student Applicant', function(assert){
	assert.expect(24);
	let done = assert.async();
	let guradian_auto_code;
	let guardian_name;
	frappe.run_serially([
		() => frappe.set_route('List', 'Guardian'),
		() => frappe.timeout(0.5),
		() => {$(`a:contains("Test Guardian"):visible`)[0].click();},
		() => frappe.timeout(1),
		() => {
			guardian_name = cur_frm.doc.guardian_name;
			guradian_auto_code = frappe.get_route()[2];
		},
		// Testing data entry for Student Applicant
		() => {
			return frappe.tests.make('Student Applicant',[
				{first_name: 'Fname'},
				{middle_name: 'Mname'},
				{last_name: 'Lname'},
				{program: 'Standard Test'},
				{student_admission: '2016-17 Admissions'},
				{academic_year: '2016-17'},
				{date_of_birth: '1995-07-20'},
				{student_email_id: 'test@testmail.com'},
				{gender: 'Male'},
				{student_mobile_number: '9898980000'},
				{blood_group: 'O+'},
				{address_line_1: 'Test appt, Test Society,'},
				{address_line_2: 'Test district, Test city.'},
				{city: 'Test'},
				{state: 'Test'},
				{pincode: '400086'}
			]);
		},
		// Entry in Guardian child table
		() => $('a:contains("Guardian Details"):visible').click(),
		() => $('.btn:contains("Add Row"):visible').click(),
		() => {
			cur_frm.get_field("guardians").grid.grid_rows[0].doc.guardian = guradian_auto_code;
			cur_frm.get_field("guardians").grid.grid_rows[0].doc.relation = "Father";
			cur_frm.get_field("guardians").grid.grid_rows[0].doc.guardian_name = guardian_name;
			$('a:contains("Guardian Details"):visible').click();
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
			assert.ok(cur_frm.doc.first_name == 'Fname');
			assert.ok(cur_frm.doc.middle_name == 'Mname');
			assert.ok(cur_frm.doc.last_name == 'Lname');
			assert.ok(cur_frm.doc.program == 'Standard Test', 'Program selected correctly');
			assert.ok(cur_frm.doc.student_admission == '2016-17 Admissions', 'Student Admission entry correctly selected');
			assert.ok(cur_frm.doc.academic_year == '2016-17');
			assert.ok(cur_frm.doc.date_of_birth == '1995-07-20');
			assert.ok(cur_frm.doc.student_email_id == 'test@testmail.com');
			assert.ok(cur_frm.doc.gender == 'Male');
			assert.ok(cur_frm.doc.student_mobile_number == '9898980000');
			assert.ok(cur_frm.doc.blood_group == 'O+');
			assert.ok(cur_frm.doc.address_line_1 == 'Test appt, Test Society,');
			assert.ok(cur_frm.doc.address_line_2 == 'Test district, Test city.');
			assert.ok(cur_frm.doc.city == 'Test');
			assert.ok(cur_frm.doc.state == 'Test');
			assert.ok(cur_frm.doc.pincode == '400086');
		},
		() => frappe.timeout(1),
		() => $('a:contains("Guardian Details"):visible').click(),
		() => {
			assert.ok(cur_frm.get_field("guardians").grid.grid_rows[0].doc.guardian == guradian_auto_code, 'Guardian correctly selected from dropdown');
			assert.ok(cur_frm.get_field("guardians").grid.grid_rows[0].doc.relation == 'Father');
			assert.ok(cur_frm.get_field("guardians").grid.grid_rows[0].doc.guardian_name == guardian_name, 'Guardian name was correctly retrieved');
		},
		() => $('a:contains("Sibling Details"):visible').click(),
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