# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TraceEntry:
	scheme: str
	status: str  # "matched" | "rejected" | "shadowed" | "error"
	reason: str = ""
	tier_idx: int | None = None


@dataclass
class PricingTrace:
	"""Why every candidate scheme did or did not apply: the support story."""

	entries: list[TraceEntry] = field(default_factory=list)

	def matched(self, scheme: str, tier_idx: int | None = None, reason: str = "") -> None:
		self.entries.append(TraceEntry(scheme, "matched", reason, tier_idx))

	def rejected(self, scheme: str, reason: str) -> None:
		self.entries.append(TraceEntry(scheme, "rejected", reason))

	def shadowed(self, scheme: str, by: str) -> None:
		self.entries.append(TraceEntry(scheme, "shadowed", f"lost to {by} on priority"))

	def error(self, scheme: str, reason: str) -> None:
		self.entries.append(TraceEntry(scheme, "error", reason))

	def as_list(self) -> list[dict]:
		return [vars(entry) for entry in self.entries]
