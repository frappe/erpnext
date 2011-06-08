SELECT `tabGL Entry`.`cost_center`,`tabAccount`.`parent_account`,sum(`tabGL Entry`.`debit`),sum(`tabGL Entry`.`credit`),sum(`tabGL Entry`.`debit`)-sum(`tabGL Entry`.`credit`) 
 FROM `tabGL Entry`,`tabAccount`
 WHERE `tabGL Entry`.`account`=`tabAccount`.`name`
 AND ifnull(`tabGL Entry`.`is_cancelled`,'No')='No'
 AND `tabAccount`.is_pl_account='Yes'
 AND `tabAccount`.debit_or_credit='Debit' 
 AND `tabGL Entry`.`posting_date`>='%(posting_date)s'
 AND `tabGL Entry`.`posting_date`<='%(posting_date1)s'
 AND `tabGL Entry`.`company` LIKE '%(company)s%%' 
 AND `tabAccount`.`parent_account` LIKE '%(account)s%%'
 AND `tabGL Entry`.`cost_center` LIKE '%(cost_center)s%%' 
 GROUP BY `tabGL Entry`.`cost_center` , `tabAccount`.`parent_account`