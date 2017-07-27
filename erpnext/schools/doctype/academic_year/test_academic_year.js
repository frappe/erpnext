// Testing Setup Module in Schools
QUnit.module('setup');

// Testing Academic Year Testing option
QUnit.test('test academic year', function(assert){
	assert.expect(3);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Academic Year', [
				{academic_year_name: '2015-16'},
				{year_start_date: '2015-07-20'},
				{year_end_date:'2016-06-20'},
			]);
		},

		() => {
			assert.ok(cur_frm.doc.academic_year_name=='2015-16');
			assert.ok(cur_frm.doc.year_start_date=='2015-07-20');
			assert.ok(cur_frm.doc.year_end_date=='2016-06-20');
		},
		() => done()
	]);
});