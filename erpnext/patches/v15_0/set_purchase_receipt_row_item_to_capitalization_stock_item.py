import frappe


def execute():
	# nosemgrep
	frappe.db.sql(
		"""
        UPDATE `tabAsset Capitalization Stock Item` ACSI
        JOIN `tabAsset Capitalization` AC
        ON ACSI.parent = AC.name
        JOIN `tabPurchase Receipt Item` PRI
        ON
            PRI.item_code = ACSI.item_code
            AND PRI.wip_composite_asset = AC.target_asset
        SET
            ACSI.purchase_receipt_item = PRI.name
        WHERE
            ACSI.purchase_receipt_item IS NULL
            AND AC.docstatus = 1
    """
	)
