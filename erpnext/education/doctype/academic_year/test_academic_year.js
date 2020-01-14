// Testing Setup Module in Education
QUnit.module('education');

QUnit.test('Test: Academic Year', function(assert){
	assert.expect(3);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Academic Year', [
				{academic_year_name: '2016-17'},
				{year_start_date: '2016-07-20'},
				{year_end_date:'2017-06-20'},
			]);
		},

		() => {
			assert.ok(cur_frm.doc.academic_year_name=='2016-17');
			assert.ok(cur_frm.doc.year_start_date=='2016-07-20');
			assert.ok(cur_frm.doc.year_end_date=='2017-06-20');
		},
		() => done()
	]);
});