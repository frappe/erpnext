/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Restaurant Reservation", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(1);

	frappe.run_serially([
		// insert a new Restaurant Reservation
		() => frappe.tests.make('Restaurant Reservation', [
			// values to be set
			{restaurant: 'Gokul - JP Nagar'},
			{customer_name: 'test customer'},
			{reservation_time: frappe.datetime.now_date() + " 19:00:00"},
			{no_of_people: 4},
		]),
		() => {
			assert.equal(cur_frm.doc.reservation_end_time,
				frappe.datetime.now_date() + ' 20:00:00');
		},
		() => done()
	]);

});
