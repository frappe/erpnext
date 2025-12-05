from dataclasses import dataclass
from typing import Optional, Sequence, Dict, Any

@dataclass
class Item:
    item_code: Optional[str] = None
    item_name: str = ""
    item_group: Optional[str] = None
    tax_category: Optional[str] = None
    item_tax_template: Optional[str] = None

    @classmethod
    def from_sequence(cls, seq: Sequence[Any]) -> "Item":
        """Create Item from a CSV row sequence (positional)."""
        values = list(seq) + [None] * (5 - len(seq))

        item_code = values[0]
        item_name = values[1]
        item_group = values[2]
        tax_category = values[3]
        item_tax_template = values[4]

        return cls(
            item_code=str(item_code).strip() if item_code not in (None, "") else None,
            item_name=str(item_name).strip() if item_name not in (None, "") else "",
            item_group=str(item_group).strip() if item_group not in (None, "") else None,
            tax_category=str(tax_category).strip() if tax_category not in (None, "") else None,
            item_tax_template=str(item_tax_template).strip() if item_tax_template not in (None, "") else None,
        )

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Item":
        """Create Item from a CSV dictionary row."""
        return cls.from_sequence([
            d.get("Item Code"),
            d.get("Item Name"),
            d.get("Item Group"),
            d.get("Tax Category"),
            d.get("Item Tax Template"),
        ])

    def to_dict(self) -> Dict[str, Any]:
        """Convert Item back to dictionary form (useful for debugging or exporting)."""
        return {
            "Item Code": self.item_code,
            "Item Name": self.item_name,
            "Item Group": self.item_group,
            "Tax Category": self.tax_category,
            "Item Tax Template": self.item_tax_template,
        }

    def __repr__(self) -> str:
        return f"Item(item_name={self.item_name!r}, item_tax_template={self.item_tax_template!r})"
