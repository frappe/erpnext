SELECT *
FROM (

SELECT a.posting_date, a.voucher_no, a.account, a.credit AS inv_amount, ifnull( a.credit, 0 ) - ifnull( b.debit, 0 ) AS outstanding
FROM (

SELECT gl . *
FROM `tabGL Entry` gl, `tabAccount` acc
WHERE gl.account = acc.name
AND acc.master_type = 'Supplier'
AND ifnull( gl.is_cancelled, 'No' ) = 'No'
AND gl.credit >0
AND gl.posting_date <= current_date
)a
LEFT JOIN (

SELECT against_voucher, account, sum( debit ) AS debit
FROM `tabGL Entry`
WHERE ifnull( is_cancelled, 'No' ) = 'No'
AND posting_date <= current_date
GROUP BY against_voucher, account
)b ON a.voucher_no = b.against_voucher
AND a.account = b.account
)c
WHERE outstanding !=0
ORDER BY posting_date, voucher_no