import frappe


def execute():
	# not using frappe.qb because https://github.com/frappe/frappe/issues/20292
	frappe.db.sql(
		"""UPDATE `tabAsset Depreciation Schedule`
        JOIN `tabAsset`
        ON `tabAsset Depreciation Schedule`.`asset`=`tabAsset`.`name`
        SET
            `tabAsset Depreciation Schedule`.`gross_purchase_amount`=`tabAsset`.`gross_purchase_amount`,
            `tabAsset Depreciation Schedule`.`number_of_depreciations_booked`=`tabAsset`.`number_of_depreciations_booked`
        WHERE
        (
            `tabAsset Depreciation Schedule`.`gross_purchase_amount`<>`tabAsset`.`gross_purchase_amount`
            OR
            `tabAsset Depreciation Schedule`.`number_of_depreciations_booked`<>`tabAsset`.`number_of_depreciations_booked`
        )
        AND `tabAsset Depreciation Schedule`.`docstatus`<2"""
	)
