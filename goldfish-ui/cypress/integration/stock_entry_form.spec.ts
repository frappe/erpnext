describe('Stock Entry Form', () => {
  it('submits a stock entry successfully', () => {
    cy.visit('/stock-entry')
    cy.get('input[name="company"]').type('Test Company')
    cy.get('select[name="purpose"]').select('Material Receipt')
    cy.get('input[name="items.0.itemCode"]').type('ITEM-001')
    cy.get('input[name="items.0.qty"]').type('10')
    cy.get('input[name="items.0.basicRate"]').type('100')
    cy.get('button[type="submit"]').click()
    cy.contains('Stock Entry created successfully').should('be.visible')
  })
})