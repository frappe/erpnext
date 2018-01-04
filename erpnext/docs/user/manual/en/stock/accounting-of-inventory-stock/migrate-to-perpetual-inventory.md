# Migrate To Perpetual Inventory

Perpetual Inventory Valuation is activated by default in the system.

For the users who are currently following periodic inventory valuation system, and wish to migrate to perpetual inventory valuation system, please follow the steps explained below.

As Perpetual Inventory always maintains a sync between stock and account balance, it is not possible to enable it with existing Warehouse setup. You have to create a whole new set of Warehouses, each linked to relevant account.

Steps:

  * Nullify the balance of account heads (stock-in-hand / fixed-asset) which you are using to maintain available stock value, through a Journal Entry.

  * As existing warehouses are linked to stock transactions which does not have corresponding accounting entries, those warehouses can not be used for perpetual inventory. You have to create new warehouses for the future stock transactions which will be linked to their respective accounts. While creating new warehouses, select an account group under which the child account for the warehouse will be created.

  * Setup the following default accounts for each Company 

    * Stock Received But Not Billed
    * Stock Adjustment Account
    * Expenses Included In Valuation
    * Cost Center
  * Activate Perpetual Inventory

	`Explore > Accounts > Accounts Settings`
	
	<img class="screenshot" alt="Perpetual Inventory" src="/docs/assets/img/accounts/perpetual-1.png">
  

  * Create Stock Entry (Material Transfer) to transfer available stock from existing warehouse to new warehouse. As stock will be available in the new warehouse, you should select the new warehouse for all the future transactions.

System will not post any accounting entries for existing stock transactions submitted prior to the activation of Perpetual Inventory as those old warehouses will not be linked to any account. If you create any new transaction or modify/amend existing transactions, with old warehouse, there will be no corresponding accounting entries. You have to manually sync stock and account balance through Journal Entry.

> Note: If you are already using old Perpetual Inventory system, it will be deactivated automatically. You need to follow the above steps to reactivate it.

