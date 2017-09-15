QUnit.module('hr');

QUnit.test("Test: Loan Type [HR]", function (assert) {
	assert.expect(2);
	let done = assert.async();

	frappe.run_serially([
		// Loan Type creation
		() => {
			frappe.tests.make('Loan Type', [
				{ loan_name: 'Test Loan'},
				{ maximum_loan_amount: 400000},
				{ rate_of_interest: 14},
				{ description:
					'This is just a test.'}
			]);
		},
		() => frappe.timeout(5),

		// Checking if the fields are correctly set
		() => {
			assert.ok(cur_frm.get_field('disabled').value==0, 'Loan Type created successfully');
			assert.ok(cur_frm.docname=='Test Loan', 'Loan title Correctly set');
		},
		() => done()
	]);
});

