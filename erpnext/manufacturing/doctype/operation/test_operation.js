QUnit.test("test: operation", function (assert) {
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([
		// test operation creation
		() => frappe.set_route("List", "Operation"),

		// Create a Keyboard operation
		() => {
			return frappe.tests.make(
				"Operation", [
					{__newname: "Assemble Keyboard"},
					{workstation: "Keyboard assembly workstation"}
				]
			);
		},
		() => frappe.timeout(3),
		() => {
			assert.ok(cur_frm.docname.includes('Assemble Keyboard'),
				'Assemble Keyboard created successfully');
			assert.ok(cur_frm.doc.workstation.includes('Keyboard assembly workstation'),
				'Keyboard assembly workstation was linked successfully');
		},

		// Create a Screen operation
		() => {
			return frappe.tests.make(
				"Operation", [
					{__newname: 'Assemble Screen'},
					{workstation: "Screen assembly workstation"}
				]
			);
		},
		() => frappe.timeout(3),

		// Create a CPU operation
		() => {
			return frappe.tests.make(
				"Operation", [
					{__newname: 'Assemble CPU'},
					{workstation: "CPU assembly workstation"}
				]
			);
		},
		() => frappe.timeout(3),

		() => done()
	]);
});
