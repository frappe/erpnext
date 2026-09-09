// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const { test } = require("node:test");
const { runInNewContext } = require("node:vm");

test("changing the reference clears an obsolete parent mapping", async () => {
	const frm = new InventoryDimensionForm();
	await frm.change("reference_document", "Customer");
	await frm.respond(0, [{ value: "customer", label: "Customer" }]);

	assert.equal(frm.doc.fetch_from_parent, "");
	assert.equal(frm.properties.hidden, false);
});

test("an empty lookup clears and hides the previous parent mapping", async () => {
	const frm = new InventoryDimensionForm();
	await frm.change("document_type", "Stock Entry Detail");
	await frm.respond(0, []);

	assert.equal(frm.doc.fetch_from_parent, "");
	assert.equal(frm.properties.hidden, true);
});

test("switching to all documents clears a field-name mapping", async () => {
	const frm = new InventoryDimensionForm();
	await frm.change("apply_to_all_doctypes", 1);

	assert.equal(frm.doc.fetch_from_parent, "");
	assert.equal(frm.requests.length, 0);
});

test("changing the reference in all-document mode clears the old mapping", async () => {
	const frm = new InventoryDimensionForm({ apply_to_all_doctypes: 1, fetch_from_parent: "Project" });
	await frm.change("reference_document", "Customer");

	assert.equal(frm.doc.fetch_from_parent, "");
});

test("refreshing options preserves a valid saved mapping", async () => {
	const frm = new InventoryDimensionForm();
	frm.trigger("set_parent_fields");
	await frm.respond(0, [{ value: "project", label: "Project" }]);

	assert.equal(frm.doc.fetch_from_parent, "project");
	assert.equal(frm.writes.length, 0);
});

test("all-document mode preserves a matching reference mapping", () => {
	const frm = new InventoryDimensionForm({ apply_to_all_doctypes: 1, fetch_from_parent: "Project" });
	frm.trigger("set_parent_fields");

	assert.equal(frm.doc.fetch_from_parent, "Project");
	assert.equal(frm.writes.length, 0);
});

test("a missing reference skips the lookup and clears the mapping", async () => {
	const frm = new InventoryDimensionForm();
	await frm.change("reference_document", "");

	assert.equal(frm.requests.length, 0);
	assert.equal(frm.doc.fetch_from_parent, "");
	assert.equal(Boolean(frm.properties.hidden), true);
});

test("a delayed child-table flag fetch populates the parent options", async () => {
	const frm = new InventoryDimensionForm({ istable: 0, fetch_from_parent: "" });
	frm.trigger("document_type");
	assert.equal(frm.requests.length, 0);
	await frm.change("istable", 1);
	await frm.respond(0, [{ value: "project", label: "Project" }]);

	assert.equal(frm.properties.hidden, false);
	assert.equal(frm.properties.options[1].value, "project");
});

test("an outdated reply cannot clear a selection for the new reference", async () => {
	const frm = new InventoryDimensionForm();
	frm.trigger("set_parent_fields");
	await frm.change("reference_document", "Customer");
	await frm.respond(1, [{ value: "customer", label: "Customer" }]);
	await frm.change("fetch_from_parent", "customer");
	await frm.respond(0, [{ value: "project", label: "Project" }]);

	assert.equal(frm.doc.fetch_from_parent, "customer");
	assert.equal(frm.properties.options[1].value, "customer");
});

test("an outdated child lookup cannot clear an all-document mapping", async () => {
	const frm = new InventoryDimensionForm();
	frm.trigger("set_parent_fields");
	await frm.change("apply_to_all_doctypes", 1);
	await frm.change("fetch_from_parent", "Project");
	await frm.respond(0, []);

	assert.equal(frm.doc.fetch_from_parent, "Project");
	assert.equal(Boolean(frm.properties.hidden), false);
});

class InventoryDimensionForm {
	constructor(values = {}) {
		this.doc = {
			reference_document: "Project",
			document_type: "Delivery Note Item",
			istable: 1,
			apply_to_all_doctypes: 0,
			fetch_from_parent: "project",
			...values,
		};
		this.properties = {};
		this.requests = [];
		this.writes = [];
		runInNewContext(readFileSync(join(__dirname, "inventory_dimension.js"), "utf8"), {
			frappe: {
				ui: { form: { on: (doctype, handlers) => (this.handlers = handlers) } },
				call: (request) => this.requests.push(request),
			},
		});
	}

	async change(field, value) {
		await this.set_value(field, value);
		return this.trigger(field);
	}

	trigger(event) {
		return this.handlers[event]?.(this);
	}

	respond(index, fields) {
		return this.requests[index].callback({ message: fields });
	}

	set_value(field, value) {
		this.writes.push({ field, value });
		this.doc[field] = value;
		return Promise.resolve();
	}

	set_df_property(field, property, value) {
		this.properties[property] = value;
	}
}
