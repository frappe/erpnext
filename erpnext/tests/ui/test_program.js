// Testing Setup Module in Schools
QUnit.module('setup');

// Testing setting Program
QUnit.test('test program', function(assert){
	assert.expect(11);
	let done = assert.async();
	frappe.run_serially([
		// () => frappe.timeout(1),
		() => frappe.tests.setup_doctype('Department'),
		() => frappe.tests.setup_doctype('Grading Scale'),
		() => frappe.tests.setup_doctype('Assessment Criteria Group'),
		() => frappe.tests.setup_doctype('Assessment Criteria'),
		() => frappe.tests.setup_doctype('Course'),
		() => frappe.tests.setup_doctype('Academic Year'),
		() => frappe.tests.setup_doctype('Academic Term'),
		() => frappe.tests.setup_doctype('Student Category'),
		() => {
			return frappe.tests.make('Program', [
				{program_name: 'Standard Test'},
				{program_code: 'Standard Test'},
				{department: 'Teaching'},
				{program_abbreviation: 'Standard Test'},
				{courses: [
					[
						{course: '007'},
						{required: true}
					]
				]}
			]);
		},

		() => cur_frm.save(),
		() => { y = cur_frm.doc.program_name; }, // Storing current Doctype name 
		
		// Setting up Fee Category to select in Program doctype
		() => frappe.tests.setup_doctype('Fee Category'),
		// Setting up Fee Structure to be selected in Program doctype
		() => frappe.tests.setup_doctype('Fee Structure'),

		() => { 
			// x = $('.ellipsis.sub-heading.text-muted').text();
			x = $(location).attr('hash'); 
			n = x.indexOf('FS00');
			x = x.substring(n);
		}, // Storing naming convention of Fee Structure entry
		
		() => frappe.set_route('Form', ('Program/'+y)), // Routing to our current Program doctype

		() => $('.shaded-section~ .visible-section+ .visible-section .grid-add-row').trigger('click'), // clicking on Add Row button
		
		// Storing data that were dependent earlier inceptionally
		() => cur_frm.doc.fees[0].academic_term = '2016-17 (Semester 1)',
		() => cur_frm.doc.fees[0].student_category = 'Scholarship',
		() => cur_frm.doc.fees[0].due_date = '2015-07-20',
		() => $('.error').trigger('click'),
		() => $('.bold.input-sm').trigger('focus'),
		() => frappe.timeout(1),
		() => $('.bold.input-sm').trigger('focus'),
		() => $('.bold.input-sm').val(x),
		() => $('.bold.input-sm').trigger('focus'),
		() => frappe.timeout(1),
		() => cur_frm.save(),

		() => {
			assert.ok(cur_frm.doc.program_name == 'Standard Test');
			assert.ok(cur_frm.doc.program_code == 'Standard Test');
			assert.ok(cur_frm.doc.department == 'Teaching');
			assert.ok(cur_frm.doc.program_abbreviation == 'Standard Test');
			assert.ok(cur_frm.doc.courses[0].course == '007');
			assert.ok(cur_frm.doc.courses[0].required == true);
			assert.ok(cur_frm.doc.fees[0].academic_term == '2016-17 (Semester 1)');
			assert.ok(cur_frm.doc.fees[0].fee_structure == x);
			assert.ok(cur_frm.doc.fees[0].student_category == 'Scholarship');
			assert.ok(cur_frm.doc.fees[0].due_date == '2015-07-20');
			assert.ok(cur_frm.doc.fees[0].amount == 20000);
		},

		() => done()
	]);
});