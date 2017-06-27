QUnit.test( "test new customer", function(assert) {
	assert.expect(2);
	let done = assert.async();
	let random = frappe.utils.get_random(10);

	frappe.set_route('List', 'Customer')
		.then(() => {
			return frappe.new_doc('Customer');
		})
		.then(() => {
			frappe.quick_entry.dialog.set_value('description', random);
			return frappe.quick_entry.insert();
		})
		.then((doc) => {
			assert.ok(doc && !doc.__islocal);
			return frappe.set_route('Form', 'ToDo', doc.name);
		})
		.then(() => {
			assert.ok(cur_frm.doc.description.includes(random));
			done();
		});
});
