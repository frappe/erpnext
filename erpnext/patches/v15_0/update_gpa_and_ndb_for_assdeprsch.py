import frappe


def execute():
	# not using frappe.qb because https://github.com/frappe/frappe/issues/20292
	frappe.db.sql(
		"""UPDATE `tabAsset Depreciation Schedule`
        JOIN `tabAsset`
        ON `tabAsset Depreciation Schedule`.`asset`=`tabAsset`.`name`
        SET
<<<<<<< HEAD
            `tabAsset Depreciation Schedule`.`net_purchase_amount`=`tabAsset`.`net_purchase_amount`,
            `tabAsset Depreciation Schedule`.`opening_number_of_booked_depreciations`=`tabAsset`.`opening_number_of_booked_depreciations`
        WHERE
        (
            `tabAsset Depreciation Schedule`.`net_purchase_amount`<>`tabAsset`.`net_purchase_amount`
=======
            `tabAsset Depreciation Schedule`.`gross_purchase_amount`=`tabAsset`.`gross_purchase_amount`,
            `tabAsset Depreciation Schedule`.`opening_number_of_booked_depreciations`=`tabAsset`.`opening_number_of_booked_depreciations`
        WHERE
        (
            `tabAsset Depreciation Schedule`.`gross_purchase_amount`<>`tabAsset`.`gross_purchase_amount`
>>>>>>> 7c4cf3e834 (Favicon.svg)
            OR
            `tabAsset Depreciation Schedule`.`opening_number_of_booked_depreciations`<>`tabAsset`.`opening_number_of_booked_depreciations`
        )
        AND `tabAsset Depreciation Schedule`.`docstatus`<2"""
	)
