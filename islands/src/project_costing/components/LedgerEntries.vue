<script setup>
import { computed, ref, watch } from "vue";
import { Button, ErrorMessage, TabButtons, useCall } from "frappe-ui";
import { ChartCard, ChartContainer } from "frappe-ui/charts";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow } from "frappe-ui/list";
import { useHost } from "@framework/ui/island";

import { ledgerReportRoute } from "../accounts.js";
import { form_route } from "../costing.js";
import { useFormat } from "../format.js";

const METHOD = "/api/v2/method/erpnext.projects.doctype.project.costing.accounts.get_ledger_entries";
const PAGE = 20;

const props = defineProps({
	accounts: { type: Object, required: true },
});
const account = defineModel("account", { type: String, default: null });

const __ = window.__;
const format = useFormat();
const host = useHost();

const kind = ref("all");
const kinds = [
	{ value: "all", label: __("All") },
	{ value: "Expense", label: __("Expense") },
	{ value: "Income", label: __("Income") },
];
const page_length = ref(PAGE);

const entries = useCall({
	url: METHOD,
	method: "GET",
	immediate: false,
	params: () => {
		const params = { project: props.accounts.project, page_length: page_length.value + 1 };
		if (account.value) params.account = account.value;
		else if (kind.value !== "all") params.root_type = kind.value;
		return params;
	},
});

// One row past the page says whether there are more.
const rows = computed(() => (entries.data || []).slice(0, page_length.value));
const has_more = computed(() => (entries.data || []).length > page_length.value);

// Synchronous, so a new filter and its first page go out as one request.
watch([account, kind], () => (page_length.value = PAGE), { flush: "sync" });
watch([account, kind, page_length, () => props.accounts], () => entries.reload(), { immediate: true });

const account_name = computed(
	() => props.accounts.rows.find((row) => row.account === account.value)?.account_name || account.value
);
const open_voucher = (row) => host.navigate?.(form_route(row.voucher_type, row.voucher_no));
const open_report = () => host.navigate?.(ledgerReportRoute(props.accounts, account.value));
</script>

<template>
	<ChartCard id="ledger-entries">
		<ChartContainer :title="__('Ledger entries')">
			<template #actions>
				<Button
					size="sm"
					variant="ghost"
					icon-right="lucide-arrow-up-right"
					:label="__('General Ledger')"
					@click="open_report"
				/>
			</template>

			<div class="mb-3 mt-2 flex flex-wrap items-center gap-2">
				<TabButtons v-if="!account" v-model="kind" :options="kinds" size="sm" />
				<Button
					v-else
					size="sm"
					:label="account_name"
					icon-right="lucide-x"
					@click="account = null"
				/>
			</div>

			<ErrorMessage v-if="entries.error" :message="entries.error.message" />
			<div v-else-if="rows.length" class="-mx-1 overflow-x-auto px-1">
				<div class="min-w-[640px]">
					<List
						:columns="['6.5rem', 'minmax(11rem,1.2fr)', 'minmax(9rem,1fr)', '6.5rem', '6.5rem']"
						:row-height="52"
					>
						<ListHeader>
							<ListHeaderCell>{{ __("Date") }}</ListHeaderCell>
							<ListHeaderCell>{{ __("Voucher") }}</ListHeaderCell>
							<ListHeaderCell>{{ __("Account") }}</ListHeaderCell>
							<ListHeaderCell class="justify-end">{{ __("Debit") }}</ListHeaderCell>
							<ListHeaderCell class="justify-end">{{ __("Credit") }}</ListHeaderCell>
						</ListHeader>
						<ListRow v-for="row in rows" :key="row.name" @click="open_voucher(row)">
							<ListCell>
								<span class="text-sm text-ink-gray-5">{{
									format.date(row.posting_date)
								}}</span>
							</ListCell>
							<ListCell>
								<div class="min-w-0">
									<p class="truncate text-sm text-ink-gray-8">{{ row.voucher_no }}</p>
									<p class="truncate text-xs text-ink-gray-5">{{ __(row.voucher_type) }}</p>
								</div>
							</ListCell>
							<ListCell>
								<span class="truncate text-sm text-ink-gray-7">{{ row.account }}</span>
							</ListCell>
							<ListCell class="justify-end">
								<span class="text-sm tabular-nums text-ink-gray-8">
									{{ row.debit ? format.money(row.debit) : "" }}
								</span>
							</ListCell>
							<ListCell class="justify-end">
								<span class="text-sm tabular-nums text-ink-gray-8">
									{{ row.credit ? format.money(row.credit) : "" }}
								</span>
							</ListCell>
						</ListRow>
					</List>
				</div>
			</div>
			<p v-else-if="entries.data" class="py-10 text-center text-p-sm text-ink-gray-4">
				{{ __("No ledger entries for this project in {0}", [accounts.fiscal_year]) }}
			</p>

			<Button
				v-if="has_more"
				class="mt-3"
				variant="ghost"
				size="sm"
				:loading="entries.loading"
				:label="__('Show more')"
				@click="page_length += PAGE"
			/>
		</ChartContainer>
	</ChartCard>
</template>
