describe("Test Item Dashboard", () => {
	before(() => {
		cy.login();
		cy.visit("/app/item");
		cy.insert_doc(
			"Item",
			{
				item_code: "e2e_test_item",
				item_group: "All Item Groups",
				opening_stock: 42,
				valuation_rate: 100,
			},
			true
		);
		cy.go_to_doc("item", "e2e_test_item");
	});

	it("should show dashboard with correct data on first load", () => {
		cy.get(".stock-levels").contains("Stock Levels").should("be.visible");
		cy.get(".stock-levels").contains("e2e_test_item").should("exist");

		// reserved and available qty
		cy.get(".stock-levels .inline-graph-count")
			.eq(0)
			.contains("0")
			.should("exist");
		cy.get(".stock-levels .inline-graph-count")
			.eq(1)
			.contains("42")
			.should("exist");
	});

	it("should persist on field change", () => {
		cy.get('input[data-fieldname="disabled"]').check();
		cy.wait(500);
		cy.get(".stock-levels").contains("Stock Levels").should("be.visible");
		cy.get(".stock-levels").should("have.length", 1);
	});

	it("should persist on reload", () => {
		cy.reload();
		cy.get(".stock-levels").contains("Stock Levels").should("be.visible");
	});
});
