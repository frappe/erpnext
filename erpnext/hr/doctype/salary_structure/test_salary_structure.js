QUnit.test("test Salary Structure", function(assert) {
	assert.expect(7);
	let done = assert.async();
	let employee_name1;

	frappe.run_serially([
		() => frappe.db.get_value('Employee', {'employee_name': "Test Employee 1"}, 'name',
			(r) => {
				employee_name1 = r.name;
			}
		),
		() => frappe.timeout(5),
		() => frappe.db.get_value('Employee', {'employee_name': "Test Employee 3"}, 'name',
			(r) => {
			// Creating Salary Structure for employees);
				return frappe.tests.make('Salary Structure', [
					{ __newname: 'Test Salary Structure'},
					{ company: 'For Testing'},
					{ payroll_frequency: 'Monthly'},
					{ employees: [
						[
							{employee: employee_name1},
							{from_date: '2017-07-01'},
							{base: 25000}
						],
						[
							{employee: r.name},
							{from_date: '2017-07-01'},
							{base: 30000}
						]
					]},
					{ earnings: [
						[
							{salary_component: 'Basic'},
							{formula: 'base * .80'}
						],
						[
							{salary_component: 'Leave Encashment'},
							{formula: 'B * .20'}
						]
					]},
					{ deductions: [
						[
							{salary_component: 'Income Tax'},
							{formula: '(B+LE) * .20'}
						]
					]},
					{ payment_account: 'CASH - FT'},
				]);
			}
		),
		() => frappe.timeout(15),
		() => {
			// To check if all the fields are correctly set
			assert.ok(cur_frm.doc.employees[0].employee_name=='Test Employee 1',
				'Employee 1 name correctly set');

			assert.ok(cur_frm.doc.employees[1].employee_name=='Test Employee 3',
				'Employee 2 name correctly set');

			assert.ok(cur_frm.doc.employees[0].base==25000,
				'Base value for first employee is correctly set');

			assert.ok(cur_frm.doc.employees[1].base==30000,
				'Base value for second employee is correctly set');

			assert.ok(cur_frm.doc.earnings[0].formula.includes('base * .80'),
				'Formula for earnings as Basic is correctly set');

			assert.ok(cur_frm.doc.earnings[1].formula.includes('B * .20'),
				'Formula for earnings as Leave Encashment is correctly set');

			assert.ok(cur_frm.doc.deductions[0].formula.includes('(B+LE) * .20'),
				'Formula for deductions as Income Tax is correctly set');
		},
		() => done()
	]);
});
