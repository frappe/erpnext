describe("Bulk Transaction Processing", () => {
	before(() => {
		cy.login();
		cy.visit("/app/website");
	});

	it("Creates To Sales Order", () => {
		cy.visit("/app/sales-order");
		cy.url().should("include", "/sales-order");
		cy.window()
			.its("frappe.csrf_token")
			.then((csrf_token) => {
				return cy
					.request({
						url: "/api/method/erpnext.tests.ui_test_bulk_transaction_processing.create_records",
						method: "POST",
						headers: {
							Accept: "application/json",
							"Content-Type": "application/json",
							"X-Frappe-CSRF-Token": csrf_token,
						},
						timeout: 60000,
					})
					.then((res) => {
						expect(res.status).eq(200);
					});
			});
		cy.wait(5000);
		cy.get(
			".list-row-head > .list-header-subject > .list-row-col > .list-check-all"
		).check({ force: true });
		cy.wait(3000);
		cy.get(".actions-btn-group > .btn-primary").click({ force: true });
		cy.wait(3000);
		cy.get(".dropdown-menu-right > .user-action > .dropdown-item")
			.contains("Sales Invoice")
			.click({ force: true });
		cy.wait(3000);
		cy.get(".modal-content > .modal-footer > .standard-actions")
			.contains("Yes")
			.click({ force: true });
		cy.contains("Creation of Sales Invoice successful");
	});
});
