#Creating Depreciation For Item

**Question:** A Fixed Asset Item has been purchased and stored in a warehouse. How can the user create a depreciation for a Fixed Asset Item?<

**Answer:**Though there is no direct, automated method to book Asset Depreciation. A suitable work around to achieve this is by creating a Stock Reconciliation Entry.

####Step 1: In the Attachment file, fill in the appropriate columns;

- _Item Code_ whose value is to be depreciated.
- _Warehouse_ in which it is stored
- _Qty_ Leave this column blank
- _Valuation rate_ Enter the Value after Depreciation

<img src="{{docs_base_path}}/assets/img/articles/kb_deprec_csv.png"><br>


####Step 2: 

In the Stock Reconciliation Form, enter the Expense account for depreciation in <i>Difference Account</i>.</p>
<img src="{{docs_base_path}}/assets/img/articles/kb_deprec_form.png" height="302" width="652">

<div class="well">Note: For more information on Stock Reconciliation, see the <a href="https://erpnext.com/user-guide/setting-up/stock-reconciliation-for-non-serialized-item" target="_blank">User Guide</a>.</div>

<div class="well"> Note: An Automated Asset Depreciation feature in on our To-Do List. See this <a href="https://github.com/frappe/erpnext/issues/191" target="_blank">Github Issue</a>.</div>