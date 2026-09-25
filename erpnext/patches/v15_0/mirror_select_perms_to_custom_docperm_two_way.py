import frappe

# `select` grants added to the shipped DocType JSON this release. A customised DocType does not
# read shipped rows at all, so mirror them into Custom DocPerm -- for those DocTypes only.
GRANTS = {
	"Account": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Manufacturing Manager",
		"Manufacturing User",
		"Purchase Master Manager",
		"Quality Manager",
		"Sales Master Manager",
		"Stock Manager",
	],
	"Activity Type": [
		"Accounts User",
		"HR User",
		"Manufacturing User",
	],
	"Asset": [
		"Accounts Manager",
		"Manufacturing Manager",
		"Manufacturing User",
		"Purchase Manager",
		"Purchase User",
		"Stock Manager",
		"Stock User",
		"System Manager",
	],
	"Asset Category": [
		"Item Manager",
	],
	"Asset Maintenance Team": [
		"Quality Manager",
	],
	"Asset Shift Factor": [
		"Quality Manager",
	],
	"BOM": [
		"Maintenance User",
		"Purchase Manager",
		"Purchase User",
		"Sales Manager",
		"Sales User",
		"Stock Manager",
		"Stock User",
	],
	"Bank": [
		"Accounts Manager",
		"Accounts User",
	],
	"Bank Account": [
		"Purchase Manager",
		"Purchase Master Manager",
		"Sales Master Manager",
		"Sales User",
	],
	"Batch": [
		"Accounts Manager",
		"Accounts User",
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Manufacturing Manager",
		"Manufacturing User",
		"Purchase Master Manager",
		"Quality Manager",
		"Sales Manager",
		"Sales Master Manager",
		"Sales User",
	],
	"Blanket Order": [
		"Maintenance Manager",
		"Maintenance User",
		"Purchase Manager",
		"Purchase User",
		"Sales Manager",
		"Sales User",
	],
	"Brand": [
		"Website Manager",
	],
	"Company": [
		"Desk User",
		"Sales Manager",
	],
	"Cost Center": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Manufacturing Manager",
		"Manufacturing User",
		"Projects Manager",
		"Projects User",
		"Purchase Master Manager",
		"Quality Manager",
		"Sales Master Manager",
		"Stock Manager",
	],
	"Coupon Code": [
		"Maintenance Manager",
		"Maintenance User",
	],
	"Customer": [
		"Delivery Manager",
		"Delivery User",
		"Employee",
		"Fulfillment User",
		"HR Manager",
		"HR User",
		"Maintenance Manager",
		"Maintenance User",
		"Projects Manager",
		"Projects User",
		"Purchase Master Manager",
		"Quality Manager",
		"Support Team",
		"Website Manager",
	],
	"Customer Group": [
		"Item Manager",
		"Maintenance Manager",
		"Maintenance User",
		"Purchase Manager",
		"Website Manager",
	],
	"Department": [
		"Accounts User",
		"Projects Manager",
		"Projects User",
		"Quality Manager",
	],
	"Driver": [
		"Fulfillment User",
		"Sales User",
		"Stock Manager",
		"Stock User",
	],
	"Employee": [
		"Accounts Manager",
		"Accounts User",
		"Delivery Manager",
		"Fleet Manager",
		"Manufacturing Manager",
		"Manufacturing User",
		"Projects User",
		"Quality Manager",
		"Sales Master Manager",
		"Stock Manager",
	],
	"Finance Book": [
		"HR Manager",
		"Manufacturing Manager",
		"Quality Manager",
	],
	"Fiscal Year": [
		"Sales Master Manager",
	],
	"Holiday List": [
		"Accounts Manager",
		"Manufacturing User",
		"Projects Manager",
		"Projects User",
		"Sales Manager",
	],
	"Incoterm": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
	],
	"Issue": [
		"Projects User",
	],
	"Issue Priority": [
		"Support Team",
	],
	"Item Tax Template": [
		"Delivery Manager",
		"Delivery User",
		"Item Manager",
		"Maintenance Manager",
		"Maintenance User",
		"Manufacturing Manager",
		"Purchase Manager",
		"Purchase User",
		"Sales Manager",
		"Sales User",
		"Stock Manager",
		"Stock User",
	],
	"Lead": [
		"Support Team",
	],
	"Location": [
		"Quality Manager",
	],
	"Loyalty Program": [
		"Sales Master Manager",
		"Sales User",
	],
	"Manufacturer": [
		"Accounts Manager",
		"Accounts User",
	],
	"Market Segment": [
		"Sales Master Manager",
	],
	"Material Request": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance User",
		"Manufacturing Manager",
	],
	"Mode of Payment": [
		"Maintenance Manager",
		"Maintenance User",
		"Purchase Manager",
		"Purchase User",
		"Sales Manager",
		"Sales User",
	],
	"Monthly Distribution": [
		"Sales Master Manager",
	],
	"POS Invoice": [
		"Sales Manager",
		"Sales User",
	],
	"POS Profile": [
		"Sales Manager",
	],
	"Payment Term": [
		"Maintenance Manager",
		"Maintenance User",
		"Purchase Manager",
		"Purchase User",
		"Sales Manager",
		"Sales User",
	],
	"Payment Terms Template": [
		"Maintenance Manager",
		"Maintenance User",
		"Purchase Manager",
		"Purchase Master Manager",
		"Purchase User",
		"Sales Manager",
		"Sales Master Manager",
		"Sales User",
	],
	"Plant Floor": [
		"Manufacturing User",
	],
	"Price List": [
		"Accounts Manager",
		"Accounts User",
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Stock Manager",
		"Website Manager",
	],
	"Product Bundle": [
		"Accounts Manager",
		"Accounts User",
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
	],
	"Project": [
		"Accounts Manager",
		"Accounts User",
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Manufacturing Manager",
		"Manufacturing User",
		"Purchase Manager",
		"Purchase Master Manager",
		"Purchase User",
		"Quality Manager",
		"Sales Manager",
		"Sales Master Manager",
		"Sales User",
		"Stock Manager",
		"Stock User",
		"Support Team",
	],
	"Project Template": [
		"Projects Manager",
		"Projects User",
	],
	"Purchase Invoice": [
		"Manufacturing Manager",
		"Quality Manager",
		"Stock Manager",
	],
	"Purchase Receipt": [
		"Delivery Manager",
		"Delivery User",
		"Quality Manager",
	],
	"Purchase Taxes and Charges Template": [
		"Accounts Manager",
		"Accounts User",
		"Manufacturing Manager",
		"Stock Manager",
	],
	"Quality Inspection": [
		"Accounts Manager",
		"Accounts User",
		"Delivery Manager",
		"Delivery User",
		"Manufacturing Manager",
		"Manufacturing User",
		"Purchase User",
		"Sales User",
		"Stock Manager",
		"Stock User",
	],
	"Sales Forecast": [
		"Stock Manager",
	],
	"Sales Order": [
		"Projects Manager",
		"Projects User",
	],
	"Sales Partner": [
		"Accounts Manager",
		"Accounts User",
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Purchase Manager",
		"Stock Manager",
		"Website Manager",
	],
	"Sales Partner Type": [
		"Sales Master Manager",
	],
	"Sales Person": [
		"Accounts Manager",
		"Accounts User",
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Stock Manager",
	],
	"Sales Taxes and Charges Template": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Stock Manager",
	],
	"Serial No": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance User",
		"Quality Manager",
	],
	"Serial and Batch Bundle": [
		"Accounts Manager",
		"Accounts User",
		"Maintenance Manager",
		"Maintenance User",
		"Quality Manager",
	],
	"Shipment Parcel Template": [
		"Stock Manager",
	],
	"Shipping Rule": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
		"Manufacturing Manager",
		"Purchase Manager",
		"Purchase User",
		"Stock Manager",
	],
	"Supplier": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance User",
		"Quality Manager",
		"Sales Master Manager",
		"Website Manager",
	],
	"Supplier Group": [
		"Sales Manager",
		"Website Manager",
	],
	"Supplier Quotation": [
		"Maintenance Manager",
		"Maintenance User",
	],
	"Task": [
		"Accounts User",
		"Employee",
		"Manufacturing User",
	],
	"Tax Category": [
		"Delivery Manager",
		"Delivery User",
		"Item Manager",
		"Maintenance Manager",
		"Maintenance User",
		"Manufacturing Manager",
		"Purchase Manager",
		"Purchase Master Manager",
		"Purchase User",
		"Sales Manager",
		"Sales Master Manager",
		"Sales User",
		"Stock Manager",
		"Stock User",
	],
	"Tax Withholding Category": [
		"Item Manager",
		"Purchase Manager",
		"Purchase Master Manager",
		"Sales Master Manager",
		"Sales User",
	],
	"Tax Withholding Group": [
		"Accounts Manager",
		"Accounts User",
		"Purchase Manager",
		"Purchase Master Manager",
		"Sales Master Manager",
		"Sales User",
	],
	"Terms and Conditions": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Maintenance User",
	],
	"Territory": [
		"Delivery Manager",
		"Delivery User",
		"Maintenance Manager",
		"Website Manager",
	],
	"UOM": [
		"Desk User",
	],
	"Vehicle": [
		"Fulfillment User",
		"Stock User",
	],
	"Warehouse": [
		"Delivery Manager",
		"Delivery User",
		"HR Manager",
		"Maintenance Manager",
		"Maintenance User",
		"Quality Manager",
		"Website Manager",
	],
}


# Two-way, not three: v16's third clause reads `Permission Log`, absent on v15. `Deleted Document`
# is not a substitute -- purged at 180 days, it would fail OPEN. Hence this patch's distinct name.

# exceptions to the select-only mirror: their shipped rows grant more. `select` does not imply
# `read` on this branch, and bom.get_bom_items() checks `read`. Payment Terms Template is the same
# shape for a different reason -- it grants `select` to `All`, so only a `read` row is worth
# anything to these six, and get_payment_terms() checks `read`.
PAIR_PTYPES = {
	("BOM", "Purchase Manager"): ("read", "select"),
	("BOM", "Purchase User"): ("read", "select"),
	("BOM", "Stock Manager"): ("read", "select"),
	("BOM", "Stock User"): ("read", "select"),
	("Company", "Sales Manager"): ("read",),
	("Material Request", "Manufacturing Manager"): ("read", "report"),
	("Payment Terms Template", "Maintenance Manager"): ("read",),
	("Payment Terms Template", "Maintenance User"): ("read",),
	("Payment Terms Template", "Purchase Manager"): ("read",),
	("Payment Terms Template", "Purchase User"): ("read",),
	("Payment Terms Template", "Sales Manager"): ("read",),
	("Payment Terms Template", "Sales User"): ("read",),
}

# Custom DocPerm defaults `read` and `export` to 1 and add_permission leaves them, so every
# ptype is written explicitly below.
PTYPES = (
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"export",
	"import",
	"share",
	"print",
	"email",
)

SAVEPOINT = "mirror_select_perms_to_custom_docperm_two_way"


def execute():
	for doctype, roles in GRANTS.items():
		if not frappe.db.exists("DocType", doctype):
			continue

		# clause 1: only DocTypes already carrying Custom DocPerm rows
		if not frappe.db.exists("Custom DocPerm", {"parent": doctype}):
			continue

		added = False

		for role in roles:
			if not frappe.db.exists("Role", role):
				continue

			# clause 2: leave any existing rule for this role and level as the site
			# configured it, whatever its ptypes
			if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
				continue

			try:
				frappe.db.savepoint(SAVEPOINT)

				row = frappe.new_doc("Custom DocPerm")
				granted = PAIR_PTYPES.get((doctype, role), ("select",))
				row.update(
					{
						"parent": doctype,
						"parenttype": "DocType",
						"parentfield": "permissions",
						"role": role,
						"permlevel": 0,
						"if_owner": 0,
					}
				)
				# PTYPES is the clearing list and deliberately excludes `select`; write that too,
				# otherwise a pair whose granted set includes it silently gets read-only
				for ptype in (*PTYPES, "select"):
					row.set(ptype, 1 if ptype in granted else 0)

				row.insert(ignore_permissions=True)
				added = True
			except Exception:
				# roll back before logging: a failed statement leaves the transaction unusable on Postgres,
				# so log_error() would fail too and the migration would stop part-written.
				frappe.db.rollback(save_point=SAVEPOINT)
				frappe.log_error(
					title="Could not add select permission",
					message=f"{doctype} / {role}\n\n{frappe.get_traceback()}",
				)

		if added:
			frappe.clear_cache(doctype=doctype)
