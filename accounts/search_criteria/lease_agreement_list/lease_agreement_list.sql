select la.name, la.account, la.invoice_amount
from `tabLease Agreement` la
where start_date between '%(date)s' and '%(date1)s' order by la.name
