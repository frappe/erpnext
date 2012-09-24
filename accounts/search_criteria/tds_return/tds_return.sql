SELECT `tabTDS Payment`.`name`,`tabTDS Payment`.`challan_no`,`tabTDS Payment Detail`.`party_name`,`tabTDS Payment Detail`.`amount_paid`,`tabTDS Payment Detail`.`date_of_payment`,`tabTDS Payment Detail`.`tds_amount`,`tabTDS Payment Detail`.`cess_on_tds`,`tabTDS Payment Detail`.`total_tax_amount`,(`tabAccount`.pan_number) AS 'PAN of the deductee'
  FROM `tabTDS Payment Detail`,`tabTDS Payment`,`tabAccount`
  WHERE `tabTDS Payment`.docstatus = 1
   AND `tabTDS Payment`.`company` LIKE '%(company)s%%'
   AND `tabTDS Payment`.`tds_category` LIKE '%(tds_category)s%%'
   AND `tabTDS Payment`.`from_date`>='%(transaction_date)s'
   AND `tabTDS Payment`.`to_date`<='%(transaction_date1)s'
   AND `tabAccount`.name = `tabTDS Payment Detail`.party_name
   AND `tabTDS Payment Detail`.`parent` = `tabTDS Payment`.`name`
 ORDER BY `PAN of the deductee` DESC