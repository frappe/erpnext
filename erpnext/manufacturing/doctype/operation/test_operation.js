QUnit.test("test: operation", function (assert) {
	assert.expect(2);
	let done = assert.async();
	let set_op_name = (text) => {
		$(`input.input-with-feedback.form-control.bold:visible`).val(`${text}`);
	};
	let click_create = () => {
		$(`.btn-primary:contains("Create"):visible`).click();
	};

	frappe.run_serially([
		// test operation creation
		() => frappe.set_route("List", "Operation"),

		// Create a Keyboard operation
		() => {
			frappe.tests.make(
				"Operation", [
					{workstation: "Keyboard assembly workstation"}
				]
			);
		},
		() => frappe.timeout(4),
		() => set_op_name("Assemble Keyboard"),
		() => frappe.timeout(0.5),
		() => click_create(),
		() => frappe.timeout(1),
		() => {
			assert.ok(cur_frm.docname.includes('Assemble Keyboard'),
				'Assemble Keyboard created successfully');
			assert.ok(cur_frm.doc.workstation.includes('Keyboard assembly workstation'),
				'Keyboard assembly workstation was linked successfully');
		},

		// Create a Screen operation
		() => {
			frappe.tests.make(
				"Operation", [
					{workstation: "Screen assembly workstation"}
				]
			);
		},
		() => frappe.timeout(4),
		() => set_op_name("Assemble Screen"),
		() => frappe.timeout(0.5),
		() => click_create(),
		() => frappe.timeout(1),

		// Create a CPU operation
		() => {
			frappe.tests.make(
				"Operation", [
					{workstation: "CPU assembly workstation"}
				]
			);
		},
		() => frappe.timeout(4),
		() => set_op_name("Assemble CPU"),
		() => frappe.timeout(0.5),
		() => click_create(),
		() => frappe.timeout(1),

		() => done()
	]);
});
