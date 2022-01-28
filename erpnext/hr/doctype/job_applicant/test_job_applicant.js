QUnit.module('hr');

QUnit.test("Test: Job Opening [HR]", function (assert) {
	assert.expect(2);
	let done = assert.async();

	frappe.run_serially([
		// Job Applicant creation
		() => {
			frappe.tests.make('Job Applicant', [
				{ applicant_name: 'Utkarsh Goswami'},
				{ email_id: 'goswamiutkarsh0@gmail.com'},
				{ job_title: 'software-developer'},
				{ cover_letter: 'Highly skilled in designing, testing, and developing software.'+
					' This is just a test.'}
			]);
		},
		() => frappe.timeout(4),
		() => frappe.set_route('List','Job Applicant'),
		() => frappe.timeout(3),
		() => {
			assert.ok(cur_list.data.length==1, 'Job Applicant created successfully');
			assert.ok(cur_list.data[0].name=='Utkarsh Goswami - goswamiutkarsh0@gmail.com - software-developer',
				'Correct job applicant with valid job title');
		},
		() => done()
	]);
});
