SELECT `tabGL Entry`.`posting_date`, CONCAT(`tabGL Entry`.`account`, "~~~", ifnull(`tabGL Entry`.`remarks`, ''), "~~~", ifnull(`tabGL Entry`.`against`,''), "~~~", ifnull(`tabGL Entry`.`voucher_type`, ''), "~~~", ifnull(`tabGL Entry`.`voucher_no`, '')), sum(`tabGL Entry`.`debit`), sum(`tabGL Entry`.`credit`)
 FROM `tabGL Entry`
 WHERE `tabGL Entry`.`is_cancelled` LIKE '%(is_cancelled)s%%'
 AND `tabGL Entry`.`posting_date`>='%(posting_date)s'
 AND `tabGL Entry`.`posting_date`<='%(posting_date1)s'
 AND `tabGL Entry`.`company` LIKE '%(company)s%%'
 AND `tabGL Entry`.`account` LIKE '%(account)s%%'
 AND `tabGL Entry`.`remarks` LIKE '%(remarks)s%%'
 AND `tabGL Entry`.`is_opening` LIKE '%(is_opening)s%%'
 AND `tabGL Entry`.`voucher_no` LIKE '%(voucher_no)s%%'
 AND `tabGL Entry`.`voucher_type` LIKE '%(voucher_type)s%%'
 GROUP BY `tabGL Entry`.`voucher_no`,`tabGL Entry`.`account`
 ORDER BY `tabGL Entry`.`posting_date` DESC