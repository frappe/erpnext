// Testing Setup Module in Schools
QUnit.module('setup');

// Testing Academic Term option
QUnit.test('test academic term', function(assert){
	assert.expect(4);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Academic Term', [
				{academic_year: '2016-17'},
				{term_name: "Semester 1"},
				{term_start_date: '2016-07-20'},
				{term_end_date:'2017-06-20'},
			]);
		},
		() => {
			assert.ok(cur_frm.doc.academic_year=='2016-17');
			assert.ok(cur_frm.doc.term_name=='Semester 1');
			assert.ok(cur_frm.doc.term_start_date=='2016-07-20');
			assert.ok(cur_frm.doc.term_end_date=='2017-06-20');
		},
		() => done()
	]);
});