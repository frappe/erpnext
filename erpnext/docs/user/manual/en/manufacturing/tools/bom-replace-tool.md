# BOM Replace Tool

Replace BOM is the utility to replace BOM of sub-assembly item, which is already updated in the BOM of Finished Good item.

To use the Production Planning Tool, go to:

> Manufacturing > Tools > BOM Replace Tool

Let's consider a scenario to understand this better.

If company manufactures computers, Bill of Material of its finished item will constitute of:

1. Monitor
1. Key Board
1. Mouse
1. CPU

Out of all the items above, CPU is asembled separately. Hence separate BOM will be created for the CPU. Following are the items from the BOM of CPU.

1. 250 GB Hard Disk
1. Mother Board
1. Processor
1. SMTP
1. DVD player

If we have more items to be added , or existing items to be edited in the BOM of CPU, then we should create new BOM for it.

1. _350 GB Hard Disk_
1. Mother Board
1. Processor
1. SMTP
1. DVD player

To update new BOM updated in the BOM of finished item, where CPU is selected as raw-material, you can use BOM Replace tool.

<img class="screenshot" alt="BOM replace Tool" src="{{docs_base_url}}/assets/img/manufacturing/bom-replace-tool.png">

In this tool, you should select Current BOM, and New BOM. On clicking Replace button, current BOM of CPU will be replaced with New BOM in the BOM of finished Item (Computer).

**Will BOM Replace Tool work for replacing finsihed item in BOM?**

No. You should Cancel and Amend current BOM, or create a new BOM for finished item.

{next}
