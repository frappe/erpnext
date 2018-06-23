QUnit.module('hr');

QUnit.test("Test: Employee [HR]", function (assert) {
	assert.expect(4);
	let done = assert.async();
	// let today_date = frappe.datetime.nowdate();
	let employee_creation = (name, joining_date, birth_date) => {
		frappe.run_serially([
		// test employee creation
			() => {
				frappe.tests.make('Employee', [
					{ employee_name: name},
					{ salutation: 'Mr'},
					{ company: 'For Testing'},
					{ date_of_joining: joining_date},
					{ date_of_birth: birth_date},
					{ employment_type: 'Test Employment Type'},
					{ holiday_list: 'Test Holiday List'},
					{ branch: 'Test Branch'},
					{ department: 'Test Department'},
					{ designation: 'Test Designation'}
				]);
			},
			() => frappe.timeout(2),
			() => {
				assert.ok(cur_frm.get_field('employee_name').value==name,
					'Name of an Employee is correctly set');
				assert.ok(cur_frm.get_field('gender').value=='Male',
					'Gender of an Employee is correctly set');
			},
		]);
	};
	frappe.run_serially([
		() => employee_creation('Test Employee 1','2017-04-01','1992-02-02'),
		() => frappe.timeout(10),
		() => employee_creation('Test Employee 3','2017-04-01','1992-02-02'),
		() => frappe.timeout(10),
		() => done()
	]);
});