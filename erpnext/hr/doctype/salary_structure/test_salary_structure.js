QUnit.test("test Salary", function(assert) {
	assert.expect(6);
	let done = assert.async();
	let employee_name;
	frappe.run_serially([
		() => frappe.db.get_value('Employee', {'employee_name': 'Test Employee 1'}, 'name'),
		(r) => {
			employee_name = r.message.name;
		},
		() => {
			// Creating Salary Structure for a employee);
			frappe.tests.make('Salary Structure', [
				{ company: 'Test Company'},
				{ payroll_frequency: 'Monthly'},
				{ employees: [
					[
						{employee: employee_name},
						{from_date: '2017-07-01'},
						{base: 25000}
					]
				]},
				{ earnings: [
					[
						{salary_component: 'Basic'},
						{formula: 'base * .80'}
					],
					[
						{salary_component: 'HRA'},
						{formula: 'b * .75'}
					],
					[
						{salary_component: 'Leave Encashment'},
						{formula: 'hra * .50'}
					]
				]},
				{ deductions: [
					[
						{salary_component: 'Income Tax'},
						{formula: '(b+hra) * .20'}
					]
				]},
				{ payment_account: 'CASH - TC'},
			]);
		},
		() => frappe.timeout(8),
		() => cur_dialog.set_value('value','Test Salary Structure'),
		() => frappe.timeout(1),
		() => frappe.click_button('Create'),
		() => {
			// To check if all the fields are correctly set
			assert.ok(cur_frm.doc.employees[0].employee_name.includes('Test Employee 1'),
				'Employee name is correctly set');
			assert.ok(cur_frm.doc.employees[0].base==25000, 'Base value is correctly set');

			assert.ok(cur_frm.doc.earnings[0].formula.includes('base * .80'),
				'Formula for earnings as Basic is correctly set');
			assert.ok(cur_frm.doc.earnings[1].formula.includes('b * .75'),
				'Formula for earnings as HRA is correctly set');
			assert.ok(cur_frm.doc.earnings[2].formula.includes('hra * .50'),
				'Formula for earnings as Leave Encashment is correctly set');

			assert.ok(cur_frm.doc.deductions[0].formula.includes('(b+hra) * .20'),
				'Formula for deductions as Income Tax is correctly set');
		},
		() => done()
	]);
});