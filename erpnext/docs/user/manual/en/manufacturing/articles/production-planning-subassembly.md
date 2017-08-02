# Production Planning Subassembly

#Production Planning & Subassembly

if you need Production Planning Tool to consider raw-materials required for the manufacturing of sub-assembly items selected in the BOM, please check following instructions to achieve the same.

Production Planning Tool has field called "Use Multi-Level BOM", checking which will consider raw-material of sub-assemblies as well in the material planning. If this field is not checked, then it will consider sub-assembly as an item, and won't consider raw-material required for the manufacturing of that sub-assembly.

<img src="{{docs_base_path}}/assets/img/articles/$SGrab_203.png">

`Use Multi-Level BOM` field is also there in the Production Order and Stock Entry. If checked, raw-materials of sub-assembly item will be consumed in the manufacturing process, and not the sub-assembly item itself.
