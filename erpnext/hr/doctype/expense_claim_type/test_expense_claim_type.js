QUnit.module('hr');

QUnit.test("Test: Expense Claim Type [HR]", function (assert) {
	assert.expect(1);
	let done = assert.async();
	let i;
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
		() => frappe.timeout(1),
		// Checking if the created type is present in the list
		() => {
			for (i = 0; i < cur_list.data.length; i++) {
				if(cur_list.data[i].name=='Test Expense Type 1')
					break;
			}
		},
		() => {
			assert.equal('Test Expense Type 1', cur_list.data[i].name,
				'Expense Claim Type created successfully');
		},
		() => done()
	]);
});

