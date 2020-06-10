QUnit.module('hr');

QUnit.test("Test: Job Offer [HR]", function (assert) {
	assert.expect(3);
	let done = assert.async();
	frappe.run_serially([
		// Job Offer Creation
		() => {
			frappe.tests.make('Job Offer', [
				{ job_applicant: 'Utkarsh Goswami - goswamiutkarsh0@gmail.com - software-developer'},
				{ applicant_name: 'Utkarsh Goswami'},
				{ status: 'Accepted'},
				{ designation: 'Software Developer'},
				{ offer_terms: [
					[
						{offer_term: 'Responsibilities'},
						{value: 'Design, installation, testing and maintenance of software systems.'}
					],
					[
						{offer_term: 'Department'},
						{value: 'Research & Development'}
					],
					[
						{offer_term: 'Probationary Period'},
						{value: 'The Probation period is for 3 months.'}
					]
				]},
			]);
		},
		() => frappe.timeout(10),
		() => frappe.click_button('Submit'),
		() => frappe.timeout(2),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(5),
		// To check if the fields are correctly set
		() => {
			assert.ok(cur_frm.get_field('status').value=='Accepted',
				'Status of job offer is correct');
			assert.ok(cur_frm.get_field('designation').value=='Software Developer',
				'Designation of applicant is correct');
		},
		() => frappe.set_route('List','Job Offer','List'),
		() => frappe.timeout(2),
		// Checking the submission of and Job Offer
		() => {
			assert.ok(cur_list.data[0].docstatus==1,'Job Offer Submitted successfully');
		},
		() => frappe.timeout(2),
		() => done()
	]);
});