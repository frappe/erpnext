// Testing Setup Module in Schools
QUnit.module('schools');

QUnit.test('Test: Program', function(assert){
	assert.expect(6);
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

		() => {
			assert.ok(cur_frm.doc.program_name == 'Standard Test');
			assert.ok(cur_frm.doc.program_code == 'Standard Test');
			assert.ok(cur_frm.doc.department == 'Test Department');
			assert.ok(cur_frm.doc.program_abbreviation == 'Standard Test');
			assert.ok(cur_frm.doc.courses[0].course == 'Test_Sub');
			assert.ok(cur_frm.doc.courses[0].required == true);
		},
		() => done()
	]);
});