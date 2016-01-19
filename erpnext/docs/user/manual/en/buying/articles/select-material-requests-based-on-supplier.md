<h1>Select Material Requests based on Supplier</h1>

<b>Question</b>: How to create a single Purchase Order from multiple Material Requests for all Items that are purchased from common Supplier?<br>
<br><b>Answer</b>:
<br>
<br>Material Requests can be individually fetched from Purchase Orders using the 'From Material Request' button. However this procedure becomes tedious when there are multiple Material Requests for items that are purchased from a single supplier.<br>
<br>A more efficient way;
<br>
<br><u><b>Step 1:</b></u> When creating a Purchase order use the <i>'For Supplier'</i> button in the form.
<br>
<br><img src="{{docs_base_url}}/assets/img/articles/kb_po_forsupp.png" height="238" width="747"><br>
<br><u><b>Step 2:</b></u> In the 'Get From Supplier' pop-up enter the Supplier name and click on <i>'Get'</i>.
<br>
<br><img src="{{docs_base_url}}/assets/img/articles/kb_po_popup.png"><br>
<br><u><b>Step 3:</b></u> All the items associated with a Material Request and having the default Supplier, will be fetched in the Items Table. Any Item that is not required can be deleted.
<br>
<br><img src="{{docs_base_url}}/assets/img/articles/kb_po_itemtable.png" height="388" width="645"><br>
<br><div class="well">Note: For this feature to map the Items correctly, the Default Supplier field in the Item Master must be filled.</div>
<br>