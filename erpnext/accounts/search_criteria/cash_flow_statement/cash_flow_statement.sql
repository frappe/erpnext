SELECT 
  DISTINCT node.name AS name 
  FROM tabAccount AS node, tabAccount AS parent 
  WHERE node.lft BETWEEN parent.lft AND parent.rgt 
    AND node.company = '%(company)s' 
    AND node.is_pl_account = 'No' 
    AND node.level=%(level)s
    AND ifnull(node.account_type,'') != 'Bank or Cash'
  ORDER BY node.lft
