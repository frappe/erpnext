from typing import List

from erpnext.administration_dashboard.tally_migration.models.entry import Entry


class Extract:
  def __init__(self, source_filename) -> None:
    self.source_filename = source_filename
    self.entries: List[Entry] = []
    self.invalid_accounts: List[str] = []
    self.invalid_items: List[str] = []
