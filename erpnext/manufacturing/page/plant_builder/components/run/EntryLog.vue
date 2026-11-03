<script setup>
import { computed, inject } from "vue";
import { __, openForm } from "../../lib/api";
import { fmt } from "../../lib/format";

const run = inject("run");
const ICONS = {
	Manufacture: "lucide-package-check",
	"Material Transfer for Manufacture": "lucide-arrow-down-to-line",
};

const rows = computed(() =>
	run.state.value.entries.map((entry) => {
		const finished = entry.items.find((row) => row.is_finished_item);
		const stage = run.state.value.stages.find((s) => s.job_cards.includes(entry.job_card));
		const title =
			entry.purpose === "Manufacture"
				? __("Manufacture · {0}", [finished?.item_name || ""])
				: __("Material Transfer · {0}", [stage?.stage_name || ""]);
		const detail = finished
			? [`${fmt(finished.qty)} ${finished.uom}`, finished.batch_ids.join(", ")]
					.filter(Boolean)
					.join(" · ")
			: __("{0} items", [entry.items.length]);
		return {
			...entry,
			title,
			detail,
			icon: ICONS[entry.purpose] || "lucide-receipt-text",
			time: String(entry.posting_time).slice(0, 5),
		};
	})
);
</script>

<template>
	<div>
		<p class="mb-1 text-sm text-ink-gray-5">{{ __("Stock entries") }}</p>
		<div v-if="rows.length" class="divide-y divide-outline-gray-1">
			<button
				v-for="row in rows"
				:key="row.name"
				type="button"
				class="grid h-[52px] w-full grid-cols-[1.75rem_minmax(0,1fr)_3rem] items-center text-left hover:bg-surface-gray-1"
				@click="openForm('Stock Entry', row.name)"
			>
				<span class="size-4 text-ink-gray-5" :class="row.icon" aria-hidden="true" />
				<div class="min-w-0">
					<p class="truncate text-sm text-ink-gray-8">{{ row.title }}</p>
					<p class="truncate text-xs text-ink-gray-5">{{ row.name }} · {{ row.detail }}</p>
				</div>
				<span class="text-right text-xs tabular-nums text-ink-gray-5">{{ row.time }}</span>
			</button>
		</div>
		<div
			v-else
			class="flex flex-col items-center gap-2 rounded-4 border border-dashed border-outline-gray-2 px-4 py-6 text-center"
		>
			<span class="lucide-receipt-text size-5 text-ink-gray-4" aria-hidden="true" />
			<p class="text-sm text-ink-gray-6">{{ __("Nothing posted yet") }}</p>
			<p class="text-p-xs text-ink-gray-5">
				{{ __("Start the Work Order to see every stock entry it makes.") }}
			</p>
		</div>
	</div>
</template>
