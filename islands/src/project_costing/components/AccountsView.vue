<script setup>
import { computed, ref } from "vue";
import { Button } from "frappe-ui";
import { ChartCard, LineChart } from "frappe-ui/charts";

import BudgetChart from "./BudgetChart.vue";
import KpiCards from "./KpiCards.vue";
import LedgerEntries from "./LedgerEntries.vue";
import { accountKpis, toAccountsView } from "../accounts.js";
import { useFormat } from "../format.js";

const props = defineProps({
	payload: { type: Object, required: true },
	// From the Project cost view: whether the project is closed.
	closed: { type: Boolean, default: false },
});
const emit = defineEmits(["changed"]);

const __ = window.__;
const format = useFormat();

const accounts = computed(() => toAccountsView(props.payload));
// Nothing in the ledger, no budget and no open orders: an empty state rather than cards of zeros.
const empty = computed(() => !accounts.value.rows.length);
const can_add = computed(() => accounts.value.access.manage_budgets && !props.closed);
const root = ref(null);

/**
 * The budget dialog is desk's: the event leaves the island's shadow root, and the Project form
 * opens the dialog. It starts on the account with the most spend and no budget.
 */
function add_budget() {
	const expense = accounts.value.expense;
	const detail = {
		account: expense.filter((row) => !row.budget && row.actual > 0).sort((a, b) => b.actual - a.actual)[0]
			?.account,
		budgeted: expense.filter((row) => row.budget).map((row) => row.account),
		on_saved: () => emit("changed"),
	};
	root.value?.dispatchEvent(
		new CustomEvent("costing-add-budget", { bubbles: true, composed: true, detail })
	);
}
const kpis = computed(() => accountKpis(accounts.value, format));
const months = computed(() =>
	accounts.value.monthly.map((row) => ({ ...row, label: format.month(row.month) }))
);
</script>

<template>
	<div v-if="empty" ref="root" class="flex flex-col items-center justify-center gap-3 py-16 text-center">
		<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
			<span class="lucide-landmark size-6" aria-hidden="true" />
		</div>
		<p class="text-base text-ink-gray-7">{{ __("Nothing in the accounts yet") }}</p>
		<Button
			v-if="can_add"
			icon-left="lucide-plus"
			:label="__('Add budget')"
			class="mt-2"
			@click="add_budget"
		/>
	</div>
	<div v-else ref="root" class="space-y-5">
		<KpiCards :items="kpis" />
		<BudgetChart
			v-if="accounts.expense.length"
			:accounts="accounts"
			:closed="closed"
			@add-budget="add_budget"
		/>
		<ChartCard v-if="accounts.has_entries || accounts.budget_count" class="h-80">
			<LineChart
				:title="accounts.budget_count ? __('Spend against budget') : __('Spend over time')"
				:data="months"
				x="label"
				:y="accounts.budget_count ? ['actual', 'budget'] : ['actual']"
				:series-config="{
					actual: { label: __('Spent') },
					budget: { label: __('Budget to date'), dashed: true },
				}"
				:y-axis="{ format: format.short, min: 0 }"
			/>
		</ChartCard>
		<LedgerEntries :accounts="accounts" />
	</div>
</template>
