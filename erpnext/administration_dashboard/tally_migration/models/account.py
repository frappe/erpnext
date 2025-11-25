from dataclasses import dataclass
from typing import Optional, Sequence, Dict, Any

@dataclass
class Account:
    """Model for a Chart of Accounts row.

    Fields correspond to columns in `sources/Chart_Of_Accounts.csv`:
    ID, Account Name, Company, Parent Account, Disable, Is Group, Account Type, Tax Rate, Frozen
    """
    id: str
    name: str
    company: Optional[str] = None
    parent: Optional[str] = None
    disabled: bool = False
    is_group: bool = False
    account_type: Optional[str] = None
    tax_rate: Optional[float] = None
    frozen: Optional[str] = None

    @classmethod
    def from_sequence(cls, seq: Sequence[Any]) -> "Account":
        """Create Account from a CSV row sequence (positional).

        Expects the ordering: ID, Account Name, Company, Parent Account, Disable, Is Group, Account Type, Tax Rate, Frozen
        """
        # Normalize length
        values = list(seq) + [None] * (9 - len(seq))

        raw_id = values[0]
        raw_name = values[1]
        company = values[2]
        parent = values[3]
        disable = values[4]
        is_group = values[5]
        account_type = values[6]
        tax_rate = values[7]
        frozen = values[8]

        # Parse booleans/flags from CSV which may be '0'/'1' or numeric
        def to_bool(val: Any) -> bool:
            if val is None:
                return False
            if isinstance(val, bool):
                return val
            try:
                ival = int(val)
                return ival != 0
            except Exception:
                sval = str(val).strip().lower()
                return sval in ("1", "true", "yes")

        # Parse tax rate as float when possible
        def to_float(val: Any) -> Optional[float]:
            if val is None or (isinstance(val, float) and (val != val)):
                return None
            try:
                return float(val)
            except Exception:
                return None

        return cls(
            id=str(raw_id) if raw_id is not None else "",
            name=str(raw_name) if raw_name is not None else "",
            company=str(company) if company not in (None, "") else None,
            parent=str(parent) if parent not in (None, "") else None,
            disabled=to_bool(disable),
            is_group=to_bool(is_group),
            account_type=str(account_type) if account_type not in (None, "") else None,
            tax_rate=to_float(tax_rate),
            frozen=str(frozen) if frozen not in (None, "") else None,
        )

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Account":
        return cls.from_sequence([
            d.get("ID"),
            d.get("Account Name"),
            d.get("Company"),
            d.get("Parent Account"),
            d.get("Disable"),
            d.get("Is Group"),
            d.get("Account Type"),
            d.get("Tax Rate"),
            d.get("Frozen"),
        ])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ID": self.id,
            "Account Name": self.name,
            "Company": self.company,
            "Parent Account": self.parent,
            "Disable": int(self.disabled),
            "Is Group": int(self.is_group),
            "Account Type": self.account_type,
            "Tax Rate": self.tax_rate,
            "Frozen": self.frozen,
        }

    def __repr__(self) -> str:  # pragma: no cover - simple readability helper
        return f"Account(id={self.id!r}, name={self.name!r}, company={self.company!r})"

