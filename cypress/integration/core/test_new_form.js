/*
	Test to verify that most used doctypes have usable "New Docuent" page.
*/

const test_new_form_doctypes = [
	"Account",
	"BOM",
	"Bank Account",
	"Batch",
	"Customer",
	"Delivery Note",
	"Item",
	"Job Card",
	"Journal Entry",
	"Landed Cost Voucher",
	"Material Request",
	"Payment Entry",
	"Payment Order",
	"Payment Request",
	"Pick List",
	"Production Plan",
	"Purchase Invoice",
	"Purchase Order",
	"Purchase Receipt",
	"Putaway Rule",
	"Quality Inspection",
	"Quotation",
	"Request for Quotation",
	"Sales Invoice",
	"Sales Order",
	"Shipment",
	"Stock Entry",
	"Stock Reconciliation",
	"Supplier Quotation",
	"Supplier",
	"Work Order",
];

describe("Test new document form views", () => {
	before(() => {
		cy.login();
	});

	test_new_form_doctypes.forEach((doctype) => {
		it(`should open new ${doctype} form without any errors`, () => {
			cy.new_doc_view(doctype);
			// wait till at least "new doctype" heading is visible
			cy.findByRole("heading", { level: 3 }).contains(doctype);
			cy.wait(1000);

			cy.window().then((win) => {
				expect(win.console.error).to.have.callCount(0);
				win.cur_frm.refresh();
			});
		});
	});
});
