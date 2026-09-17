import frappe

# `select` grants added to the shipped DocType JSON in this release, so that roles
# which can write a form can also use its link pickers.
#
# A DocType whose permissions have been customised does not read the shipped rows at
# all: get_valid_perms() keeps a shipped DocPerm row only when its parent has no
# Custom DocPerm row, so on those DocTypes the new grants never take effect and the
# pickers stay empty. Mirror them into Custom DocPerm, for those DocTypes only.
#
# DocTypes that have not been customised are deliberately left alone -- they read the
# shipped JSON, they already have these rows, and creating Custom DocPerm rows for
# them would permanently detach them from future permission updates.
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
		"Manufacturing Manager",
		"Manufacturing User",
		"Purchase Manager",
		"Purchase User",
		"Stock Manager",
		"Stock User",
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


# Custom DocPerm defaults `read` and `export` to 1, and frappe.permissions.add_permission
# leaves those defaults in place, so every ptype is written explicitly here: these rows
# grant `select` and nothing else, exactly like the shipped rows they stand in for.
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


def execute():
	for doctype, roles in GRANTS.items():
		if not frappe.db.exists("DocType", doctype):
			continue

		# only DocTypes already carrying Custom DocPerm rows
		if not frappe.db.exists("Custom DocPerm", {"parent": doctype}):
			continue

		added = False

		for role in roles:
			if not frappe.db.exists("Role", role):
				continue

			# leave any existing rule for this role and level as the site configured it
			if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
				continue

			row = frappe.new_doc("Custom DocPerm")
			row.update(
				{
					"parent": doctype,
					"parenttype": "DocType",
					"parentfield": "permissions",
					"role": role,
					"permlevel": 0,
					"if_owner": 0,
					"select": 1,
				}
			)
			for ptype in PTYPES:
				row.set(ptype, 0)

			try:
				row.insert(ignore_permissions=True)
				added = True
			except Exception:
				# a pre-existing invalid rule must not stop the migration
				frappe.log_error(
					title="Could not add select permission",
					message=f"{doctype} / {role}\n\n{frappe.get_traceback()}",
				)

		if added:
			frappe.clear_cache(doctype=doctype)
