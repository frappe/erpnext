QUnit.module('hr');

QUnit.test("Test: Expense Claim Type [HR]", function (assert) {
	assert.expect(1);
	let done = assert.async();
	frappe.run_serially([
		// Creating a Expense Claim Type
		() => {
			frappe.tests.make('Expense Claim Type', [
				{ expense_type: 'Test Expense Type 1'},
				{ description:'This is just a test'},
				{ accounts: [
					[
						{ company: 'For Testing'},
						{ default_account: 'Rounded Off - FT'}
					]
				]},
			]);
		},
		() => frappe.timeout(5),

		// Checking if the created type is present in the list
		() => {
			assert.equal('Test Expense Type 1', cur_frm.doc.expense_type,
				'Expense Claim Type created successfully');
		},
		() => done()
	]);
});
