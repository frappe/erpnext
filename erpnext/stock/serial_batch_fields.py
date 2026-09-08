SERIAL_TEXT_DOCTYPES = (
	"Asset Capitalization Stock Item",
	"Asset Repair Consumed Item",
	"Delivery Note Item",
	"Installation Note Item",
	"Maintenance Schedule Detail",
	"Maintenance Schedule Item",
	"POS Invoice Item",
	"Packed Item",
	"Pick List Item",
	"Purchase Invoice Item",
	"Purchase Receipt Item",
	"Purchase Receipt Item Supplied",
	"Sales Invoice Item",
	"Stock Entry Detail",
	"Stock Ledger Entry",
	"Stock Reconciliation Item",
	"Subcontracting Receipt Item",
	"Subcontracting Receipt Supplied Item",
)

NUMBER_INPUT_DOCTYPES = tuple(doctype for doctype in SERIAL_TEXT_DOCTYPES if doctype != "Stock Ledger Entry")
