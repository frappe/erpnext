SELECT DISTINCT `tabGL Entry`.`Aging_date`,`tabGL Entry`.`transaction_date`,`tabGL Entry`.`account`, `tabGL Entry`.`against_voucher_type`, `tabGL Entry`.`against_voucher`,`tabGL Entry`.`voucher_type`,`tabGL Entry`.`voucher_no`, `tabGL Entry`.`remarks`, `tabGL Entry`.`credit`
FROM `tabGL Entry`,`tabAccount` 
WHERE `tabGL Entry`.`posting_date`>= '%(posting_date)s'
 AND `tabGL Entry`.`posting_date`<= '%(posting_date1)s'
 AND `tabGL Entry`.`account` LIKE '%(account)s%%'
 AND `tabGL Entry`.`company` LIKE '%(company)s%%'
 AND ((ifnull(`tabGL Entry`.voucher_type,'') = 'Payable Voucher' and `tabGL Entry`.credit>0) OR `tabGL Entry`.voucher_type = 'Journal Voucher')
 AND `tabGL Entry`.`is_cancelled` = 'No'
 AND `tabAccount`.master_type = 'Supplier'
 AND `tabAccount`.name = `tabGL Entry`.account
 ORDER BY `tabGL Entry`.`posting_date`
