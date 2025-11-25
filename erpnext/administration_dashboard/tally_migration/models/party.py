from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class Party:
    """Simple model for a party (supplier or customer).

    Fields:
      - id: the ID column from the CSV (string)
      - name: the supplier/customer name
      - type: either 'Supplier' or 'Customer'
    """
    id: str
    name: str
    type: str

    @classmethod
    def from_dict(cls, d: Dict[str, Any], party_type: str) -> "Party":
        # Since the same model is used for both supplier and customer CSVs,  
        name = None
        for key in ("Supplier Name", "Customer Name", "Name"):
            if key in d and d.get(key) not in (None, ""):
                name = d.get(key)
                break

        # Fallback to a generic 'Name' or an empty string if nothing found
        name = name if name is not None else (d.get("Name") or "")

        # ID column is usually 'ID'
        raw_id = d.get("ID")

        return cls(id=str(raw_id) if raw_id is not None else "", name=str(name), type=str(party_type))
