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
						{ company: 'Test Company'},
						{ default_account: 'Marketing Expenses - TC'}
					]
				]},
			]);
		},
		() => frappe.timeout(3),
		() => frappe.set_route('List','Expense Claim Type'),
		// Checking if the created type is present in the list
		() => frappe.timeout(2),
		() => {
			assert.equal('Test Expense Type 1', cur_list.data[0].name,
				'Expense Claim Type created successfully');
		},
		() => done()
	]);
});

