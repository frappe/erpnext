<!-- title: erpnext.stock.stock_ledger --><div class="dev-header">

<a class="btn btn-default btn-sm" disabled style="margin-bottom: 10px;">
	Version 6.x.x</a>


	<a class="btn btn-default btn-sm" href="https://github.com/frappe/erpnext/blob/develop/erpnext/stock/stock_ledger.py"
		target="_blank" style="margin-left: 10px; margin-bottom: 10px;"><i class="octicon octicon-mark-github"></i> Source</a>

</div>





	
        
	<h3 style="font-weight: normal;">Class <b>NegativeStockError</b></h3>
    
    <p style="padding-left: 30px;"><i>Inherits from frappe.exceptions.ValidationError</i></h4>
    
    <div class="docs-attr-desc"><p></p>
</div>
    <div style="padding-left: 30px;">
        
    </div>
    <hr>

	

	
        
    
    
	<p class="docs-attr-name">
        <a name="erpnext.stock.stock_ledger.delete_cancelled_entry" href="#erpnext.stock.stock_ledger.delete_cancelled_entry" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		erpnext.stock.stock_ledger.<b>delete_cancelled_entry</b>
        <i class="text-muted">(voucher_type, voucher_no)</i>
    </p>
	<div class="docs-attr-desc"><p><span class="text-muted">No docs</span></p>
</div>
	<br>

	

	
        
    
    
	<p class="docs-attr-name">
        <a name="erpnext.stock.stock_ledger.get_previous_sle" href="#erpnext.stock.stock_ledger.get_previous_sle" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		erpnext.stock.stock_ledger.<b>get_previous_sle</b>
        <i class="text-muted">(args, for_update=False)</i>
    </p>
	<div class="docs-attr-desc"><p>get the last sle on or before the current time-bucket,
to get actual qty before transaction, this function
is called from various transaction like stock entry, reco etc</p>

<p>args = {
    "item<em>code": "ABC",
    "warehouse": "XYZ",
    "posting</em>date": "2012-12-12",
    "posting_time": "12:00",
    "sle": "name of reference Stock Ledger Entry"
}</p>
</div>
	<br>

	

	
        
    
    
	<p class="docs-attr-name">
        <a name="erpnext.stock.stock_ledger.get_stock_ledger_entries" href="#erpnext.stock.stock_ledger.get_stock_ledger_entries" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		erpnext.stock.stock_ledger.<b>get_stock_ledger_entries</b>
        <i class="text-muted">(previous_sle, operator=None, order=desc, limit=None, for_update=False, debug=False)</i>
    </p>
	<div class="docs-attr-desc"><p>get stock ledger entries filtered by specific posting datetime conditions</p>
</div>
	<br>

	

	
        
    
    
	<p class="docs-attr-name">
        <a name="erpnext.stock.stock_ledger.get_valuation_rate" href="#erpnext.stock.stock_ledger.get_valuation_rate" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		erpnext.stock.stock_ledger.<b>get_valuation_rate</b>
        <i class="text-muted">(item_code, warehouse, allow_zero_rate=False)</i>
    </p>
	<div class="docs-attr-desc"><p><span class="text-muted">No docs</span></p>
</div>
	<br>

	

	
        
    
    
	<p class="docs-attr-name">
        <a name="erpnext.stock.stock_ledger.make_entry" href="#erpnext.stock.stock_ledger.make_entry" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		erpnext.stock.stock_ledger.<b>make_entry</b>
        <i class="text-muted">(args, allow_negative_stock=False, via_landed_cost_voucher=False)</i>
    </p>
	<div class="docs-attr-desc"><p><span class="text-muted">No docs</span></p>
</div>
	<br>

	

	
        
    
    
	<p class="docs-attr-name">
        <a name="erpnext.stock.stock_ledger.make_sl_entries" href="#erpnext.stock.stock_ledger.make_sl_entries" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		erpnext.stock.stock_ledger.<b>make_sl_entries</b>
        <i class="text-muted">(sl_entries, is_amended=None, allow_negative_stock=False, via_landed_cost_voucher=False)</i>
    </p>
	<div class="docs-attr-desc"><p><span class="text-muted">No docs</span></p>
</div>
	<br>

	

	
        
    
    
	<p class="docs-attr-name">
        <a name="erpnext.stock.stock_ledger.set_as_cancel" href="#erpnext.stock.stock_ledger.set_as_cancel" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		erpnext.stock.stock_ledger.<b>set_as_cancel</b>
        <i class="text-muted">(voucher_type, voucher_no)</i>
    </p>
	<div class="docs-attr-desc"><p><span class="text-muted">No docs</span></p>
</div>
	<br>

	

	
        
	<h3 style="font-weight: normal;">Class <b>update_entries_after</b></h3>
    
    <p style="padding-left: 30px;"><i>Inherits from __builtin__.object</i></h4>
    
    <div class="docs-attr-desc"><p>update valution rate and qty after transaction
from the current time-bucket onwards</p>

<p><strong>Parameters:</strong></p>

<ul>
<li><p><strong><code>args</code></strong> -  args as dict</p>

<p>args = {
    "item<em>code": "ABC",
    "warehouse": "XYZ",
    "posting</em>date": "2012-12-12",
    "posting_time": "12:00"
}</p></li>
</ul>
</div>
    <div style="padding-left: 30px;">
        
        
    
    
	<p class="docs-attr-name">
        <a name="__init__" href="#__init__" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		<b>__init__</b>
        <i class="text-muted">(self, args, allow_zero_rate=False, allow_negative_stock=None, via_landed_cost_voucher=False, verbose=1)</i>
    </p>
	<div class="docs-attr-desc"><p><span class="text-muted">No docs</span></p>
</div>
	<br>

        
        
    
    
	<p class="docs-attr-name">
        <a name="build" href="#build" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		<b>build</b>
        <i class="text-muted">(self)</i>
    </p>
	<div class="docs-attr-desc"><p><span class="text-muted">No docs</span></p>
</div>
	<br>

        
        
    
    
	<p class="docs-attr-name">
        <a name="get_fifo_values" href="#get_fifo_values" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		<b>get_fifo_values</b>
        <i class="text-muted">(self, sle)</i>
    </p>
	<div class="docs-attr-desc"><p><span class="text-muted">No docs</span></p>
</div>
	<br>

        
        
    
    
	<p class="docs-attr-name">
        <a name="get_moving_average_values" href="#get_moving_average_values" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		<b>get_moving_average_values</b>
        <i class="text-muted">(self, sle)</i>
    </p>
	<div class="docs-attr-desc"><p><span class="text-muted">No docs</span></p>
</div>
	<br>

        
        
    
    
	<p class="docs-attr-name">
        <a name="get_serialized_values" href="#get_serialized_values" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		<b>get_serialized_values</b>
        <i class="text-muted">(self, sle)</i>
    </p>
	<div class="docs-attr-desc"><p><span class="text-muted">No docs</span></p>
</div>
	<br>

        
        
    
    
	<p class="docs-attr-name">
        <a name="get_sle_after_datetime" href="#get_sle_after_datetime" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		<b>get_sle_after_datetime</b>
        <i class="text-muted">(self)</i>
    </p>
	<div class="docs-attr-desc"><p>get Stock Ledger Entries after a particular datetime, for reposting</p>
</div>
	<br>

        
        
    
    
	<p class="docs-attr-name">
        <a name="get_sle_before_datetime" href="#get_sle_before_datetime" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		<b>get_sle_before_datetime</b>
        <i class="text-muted">(self)</i>
    </p>
	<div class="docs-attr-desc"><p>get previous stock ledger entry before current time-bucket</p>
</div>
	<br>

        
        
    
    
	<p class="docs-attr-name">
        <a name="process_sle" href="#process_sle" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		<b>process_sle</b>
        <i class="text-muted">(self, sle)</i>
    </p>
	<div class="docs-attr-desc"><p><span class="text-muted">No docs</span></p>
</div>
	<br>

        
        
    
    
	<p class="docs-attr-name">
        <a name="raise_exceptions" href="#raise_exceptions" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		<b>raise_exceptions</b>
        <i class="text-muted">(self)</i>
    </p>
	<div class="docs-attr-desc"><p><span class="text-muted">No docs</span></p>
</div>
	<br>

        
        
    
    
	<p class="docs-attr-name">
        <a name="update_bin" href="#update_bin" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		<b>update_bin</b>
        <i class="text-muted">(self)</i>
    </p>
	<div class="docs-attr-desc"><p><span class="text-muted">No docs</span></p>
</div>
	<br>

        
        
    
    
	<p class="docs-attr-name">
        <a name="validate_negative_stock" href="#validate_negative_stock" class="text-muted small">
            <i class="icon-link small" style="color: #ccc;"></i></a>
		<b>validate_negative_stock</b>
        <i class="text-muted">(self, sle)</i>
    </p>
	<div class="docs-attr-desc"><p>validate negative stock for entries current datetime onwards
will not consider cancelled entries</p>
</div>
	<br>

        
    </div>
    <hr>

	



<!-- autodoc -->