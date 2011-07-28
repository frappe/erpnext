select la.name,la.account,lai.amount,cast('%(date)s' as date)-due_date as age

from `tabLease Agreement` la,`tabLease Installment` lai

where la.name=lai.parent and lai.due_date<cast('%(date)s' as date) and (lai.cheque_date is null or lai.cheque_date > cast('%(date)s' as date))

order by cast('%(date)s' as date)-due_date desc