<script setup>
import { computed, nextTick, ref } from "vue";
import { Button } from "frappe-ui";
import { ChartCard, LineChart } from "frappe-ui/charts";
import { useHost } from "@framework/ui/island";

import BudgetChart from "./BudgetChart.vue";
import KpiCards from "./KpiCards.vue";
import LedgerEntries from "./LedgerEntries.vue";
import { accountKpis, newBudgetRoute, toAccountsView } from "../accounts.js";
import { useFormat } from "../format.js";

const props = defineProps({
	payload: { type: Object, required: true },
	// From the Project cost view: whether the project is closed.
	closed: { type: Boolean, default: false },
	// The project has timesheet labour, which the ledger leaves out.
	has_labour: { type: Boolean, default: false },
});

const __ = window.__;
const format = useFormat();
const host = useHost();

const accounts = computed(() => toAccountsView(props.payload));
// Nothing in the ledger, no budget and no open orders: an empty state rather than cards of zeros.
const empty = computed(() => !accounts.value.rows.length);
const can_add = computed(() => accounts.value.access.manage_budgets && !props.closed);
const kpis = computed(() => accountKpis(accounts.value, format, { has_labour: props.has_labour }));
const months = computed(() =>
	accounts.value.monthly.map((row) => ({ ...row, label: format.month(row.month) }))
);

const account = ref(null);
function select(name) {
	account.value = name;
	nextTick(() =>
		document.getElementById("ledger-entries")?.scrollIntoView({ behavior: "smooth", block: "start" })
	);
}
</script>

<template>
	<div v-if="empty" class="flex flex-col items-center justify-center gap-3 py-16 text-center">
		<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
			<span class="lucide-landmark size-6" aria-hidden="true" />
		</div>
		<p class="text-base text-ink-gray-7">{{ __("Nothing in the accounts yet") }}</p>
		<Button
			v-if="can_add"
			variant="solid"
			theme="gray"
			icon-left="lucide-plus"
			:label="__('Add budget')"
			class="mt-2"
			@click="host.navigate?.(newBudgetRoute(accounts))"
		/>
	</div>
	<div v-else class="space-y-5">
		<KpiCards :items="kpis" />
		<BudgetChart v-if="accounts.expense.length" :accounts="accounts" :closed="closed" @select="select" />
		<ChartCard v-if="accounts.has_entries || accounts.budget_count" class="h-80">
			<LineChart
				:title="accounts.budget_count ? __('Spend against budget') : __('Spend over time')"
				:data="months"
				x="label"
				:y="accounts.budget_count ? ['actual', 'budget'] : ['actual']"
				:series-config="{
					actual: { label: __('Actual') },
					budget: { label: __('Budget to date'), dashed: true },
				}"
				:y-axis="{ format: format.short, min: 0 }"
			/>
		</ChartCard>
		<LedgerEntries v-model:account="account" :accounts="accounts" />
	</div>
</template>
