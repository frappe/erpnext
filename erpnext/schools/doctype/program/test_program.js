// Testing Setup Module in Schools
QUnit.module('schools');

QUnit.test('Test: Program', function(assert){
	assert.expect(11);
	let done = assert.async();
	let fee_structure_code;
	frappe.run_serially([
		() => {
			return frappe.tests.make('Program', [
				{program_name: 'Standard Test'},
				{program_code: 'Standard Test'},
				{department: 'Test Department'},
				{program_abbreviation: 'Standard Test'},
				{courses: [
					[
						{course: 'Test_Sub'},
						{required: true}
					]
				]}
			]);
		},

		() => cur_frm.save(),
		// Setting up Fee Category to select in Program doctype
		() => {
			return frappe.tests.make('Fee Category', [
				{category_name: 'Reservation'},
				{description: 'Special Provision'}
			]);
		},
		// Setting up Fee Structure to be selected in Program doctype
		() => {
			return frappe.tests.make('Fee Structure', [
				{program: 'Standard Test'},
				{academic_term: '2016-17 (Semester 1)'},
				{student_category: 'Reservation'},
				{components: [
					[
						{fees_category: 'Reservation'},
						{amount: 20000}
					]
				]}
			]);
		},
		() => {fee_structure_code = frappe.get_route()[2];}, // Storing naming convention of Fee Structure entry
		() => frappe.set_route('Form', ('Program/Standard Test')), // Routing to our current Program doctype

		() => $('.shaded-section~ .visible-section+ .visible-section .grid-add-row').trigger('click'), // clicking on Add Row button
		// Storing data that were inter-dependent
		() => cur_frm.doc.fees[0].academic_term = '2016-17 (Semester 1)',
		() => cur_frm.doc.fees[0].student_category = 'Reservation',
		() => cur_frm.doc.fees[0].due_date = '2016-08-20',
		() => $('.error').trigger('click'),
		() => $('.bold.input-sm').trigger('focus'),
		() => frappe.timeout(1),
		() => $('.bold.input-sm').trigger('focus'),
		() => $('.bold.input-sm').val(fee_structure_code),
		() => $('.bold.input-sm').trigger('focus'),
		() => frappe.timeout(1),
		() => cur_frm.save(),

		() => {
			assert.ok(cur_frm.doc.program_name == 'Standard Test');
			assert.ok(cur_frm.doc.program_code == 'Standard Test');
			assert.ok(cur_frm.doc.department == 'Test Department');
			assert.ok(cur_frm.doc.program_abbreviation == 'Standard Test');
			assert.ok(cur_frm.doc.courses[0].course == 'Test_Sub');
			assert.ok(cur_frm.doc.courses[0].required == true);
			assert.ok(cur_frm.doc.fees[0].academic_term == '2016-17 (Semester 1)');
			assert.ok(cur_frm.doc.fees[0].fee_structure == fee_structure_code);
			assert.ok(cur_frm.doc.fees[0].student_category == 'Reservation');
			assert.ok(cur_frm.doc.fees[0].due_date == '2016-08-20');
			assert.ok(cur_frm.doc.fees[0].amount == 20000);
		},
		() => done()
	]);
});