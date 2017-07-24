QUnit.test("test: operation", function (assert) {
	assert.expect(6);
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
					{workstation: "Keyboard WS"}
				]
			);
		},
		() => frappe.timeout(4),
		() => set_op_name("Keyboard OP"),
		() => frappe.timeout(0.5),
		() => click_create(),
		() => frappe.timeout(1),
		() => {
			assert.ok(cur_frm.docname.includes('Keyboard OP'),
				'Keyboard OP created successfully');
			assert.ok(cur_frm.doc.workstation.includes('Keyboard WS'),
				'Keyboard WS was linked successfully');
		},

		// Create a Screen operation
		() => {
			frappe.tests.make(
				"Operation", [
					{workstation: "Screen WS"}
				]
			);
		},
		() => frappe.timeout(4),
		() => set_op_name("Screen OP"),
		() => frappe.timeout(0.5),
		() => click_create(),
		() => frappe.timeout(1),
		() => {
			assert.ok(cur_frm.docname.includes('Screen OP'),
				'Screen OP created successfully');
			assert.ok(cur_frm.doc.workstation.includes('Screen WS'),
				'Screen WS was linked successfully');
		},

		// Create a CPU operation
		() => {
			frappe.tests.make(
				"Operation", [
					{workstation: "CPU WS"}
				]
			);
		},
		() => frappe.timeout(4),
		() => set_op_name("CPU OP"),
		() => frappe.timeout(0.5),
		() => click_create(),
		() => frappe.timeout(1),
		() => {
			assert.ok(cur_frm.docname.includes('CPU OP'),
				'CPU OP created successfully');
			assert.ok(cur_frm.doc.workstation.includes('CPU WS'),
				'CPU WS was linked successfully');
		},

		() => done()
	]);
});
