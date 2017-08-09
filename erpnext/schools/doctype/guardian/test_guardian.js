// Testing Student Module in Schools
QUnit.module('schools');

QUnit.test('Test: Guardian', function(assert){
	assert.expect(9);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Guardian', [
				{guardian_name: 'Test Guardian'},
				{email_address: 'guardian@testmail.com'},
				{mobile_number: 9898980000},
				{alternate_number: 8989890000},
				{date_of_birth: '1982-07-22'},
				{education: 'Testing'},
				{occupation: 'Testing'},
				{designation: 'Testing'},
				{work_address: 'Testing address'}
			]);
		},
		() => {
			assert.ok(cur_frm.doc.guardian_name == 'Test Guardian');
			assert.ok(cur_frm.doc.email_address == 'guardian@testmail.com');
			assert.ok(cur_frm.doc.mobile_number == 9898980000);
			assert.ok(cur_frm.doc.alternate_number == 8989890000);
			assert.ok(cur_frm.doc.date_of_birth == '1982-07-22');
			assert.ok(cur_frm.doc.education == 'Testing');
			assert.ok(cur_frm.doc.occupation == 'Testing');
			assert.ok(cur_frm.doc.designation == 'Testing');
			assert.ok(cur_frm.doc.work_address == 'Testing address');
		},
		() => done()
	]);
});