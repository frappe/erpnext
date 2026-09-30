import BankAccountBalancePanel from "@/components/features/BankReconciliation/BankBalance"
import BankPicker from "@/components/features/BankReconciliation/BankPicker"
import BankRecDateFilter from "@/components/features/BankReconciliation/BankRecDateFilter"
import BankTransactionUnreconcileModal from "@/components/features/BankReconciliation/BankTransactionUnreconcileModal"
import CompanySelector from "@/components/features/BankReconciliation/CompanySelector"
import MatchAndReconcile from "@/components/features/BankReconciliation/MatchAndReconcile"
import Settings from "@/components/features/Settings/Settings"
import ActionLog from "@/components/features/ActionLog/ActionLog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TooltipProvider } from "@/components/ui/tooltip"
import _ from "@/lib/translate"
import { lazy, Suspense } from "react"
import { AlertTriangleIcon, CheckCircleIcon, HomeIcon, LandmarkIcon, ListIcon, Loader2Icon, ScrollTextIcon, ShuffleIcon } from "lucide-react"
import { Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { Button } from "@/components/ui/button"
import { useAtomValue } from "jotai"
import { selectedBankAccountAtom } from "@/components/features/BankReconciliation/bankRecAtoms"

const BankReconciliationStatement = lazy(() => import('@/components/features/BankReconciliation/BankReconciliationStatement'))
const BankTransactions = lazy(() => import('@/components/features/BankReconciliation/BankTransactionList'))
const BankClearanceSummary = lazy(() => import('@/components/features/BankReconciliation/BankClearanceSummary'))
const IncorrectlyClearedEntries = lazy(() => import('@/components/features/BankReconciliation/IncorrectlyClearedEntries'))

const BankReconciliation = () => {

    return (
        <div>
            {/* The page owns the viewport height and the tabs/lists below fill what's left, so
                the virtualizers size themselves from layout instead of a measured pixel value. */}
            <div className="px-2 pt-1 flex-col gap-4 md:flex hidden h-dvh">
                <div className="flex flex-col gap-4 shrink-0">
                    <div className="flex justify-between shrink-0">
                        <div className="flex items-center gap-6">
                            <Breadcrumb>
                                <BreadcrumbList>
                                    <BreadcrumbItem>
                                        <a href="/desk" className="text-ink-gray-7">
                                            <HomeIcon size={16} />
                                        </a>
                                    </BreadcrumbItem>
                                    <BreadcrumbSeparator />
                                    <BreadcrumbItem>
                                        <BreadcrumbPage>
                                            <div className="flex gap-1 items-center">
                                                {_("Banking")}
                                            </div>

                                        </BreadcrumbPage>
                                    </BreadcrumbItem>
                                </BreadcrumbList>
                            </Breadcrumb>
                            <CompanySelector />
                        </div>
                        <div className="flex items-center gap-2">
                            <TooltipProvider>
                                <Settings />
                                <ActionLog />
                            </TooltipProvider>
                            <BankRecDateFilter />
                        </div>
                    </div>
                </div>
                <BankRecWorkspace />
                <BankTransactionUnreconcileModal />
            </div>
            <div className="md:hidden flex h-screen items-center justify-between">
                <Empty>
                    <EmptyMedia>
                        <LandmarkIcon />
                    </EmptyMedia>
                    <EmptyHeader>
                        <EmptyTitle>
                            {_("Banking")}
                        </EmptyTitle>
                        <EmptyDescription>
                            {_("This screen is not supported on mobile devices.")}
                        </EmptyDescription>
                    </EmptyHeader>
                    <EmptyContent>
                        <Button asChild>
                            <a href="/desk">
                                {_("Go to Desktop")}
                            </a>
                        </Button>
                    </EmptyContent>
                </Empty>

            </div>
        </div>
    )
}

const BankRecWorkspace = () => {
    const selectedBankAccount = useAtomValue(selectedBankAccountAtom)

    return <Tabs defaultValue="Match and Reconcile" className="min-h-0 flex-1 gap-4">
        {/* Picker + tab strip stack on the left, balance panel beside them - the tab strip
            fills height the panel needs anyway, so it costs no row of its own. The picker
            scrolls horizontally (`min-w-0` lets it shrink so its overflow-x engages) while
            the panel stays put, so the figures never scroll away. */}
        {/* No gap here: the panel's own `border-s ps-4` supplies the separation, and a gap
            would leave dead space the picker's edge fade can't reach. */}
        <div className="flex shrink-0 items-stretch">
            <div className="flex min-w-0 flex-1 flex-col justify-between gap-3">
                <BankPicker />
                {selectedBankAccount && <TabsList>
                    <TabsTrigger value="Match and Reconcile"><ShuffleIcon /> {_("Match and Reconcile")}</TabsTrigger>
                    <TabsTrigger value="Bank Reconciliation Statement"><ScrollTextIcon /> {_("Reconciliation Statement")}</TabsTrigger>
                    <TabsTrigger value="Bank Transactions"><ListIcon />{_("Transactions")}</TabsTrigger>
                    <TabsTrigger value="Bank Clearance Summary"><CheckCircleIcon />{_("Clearance Summary")}</TabsTrigger>
                    <TabsTrigger value="Incorrectly Cleared Entries"><AlertTriangleIcon /> {_("Incorrectly Cleared")}</TabsTrigger>
                </TabsList>}
            </div>
            {selectedBankAccount && <BankAccountBalancePanel />}
        </div>

        {selectedBankAccount && <>
            <TabsContent value="Match and Reconcile" className="flex min-h-0 flex-col">
                <MatchAndReconcile />
            </TabsContent>
            <Suspense fallback={
                <div className="flex items-center justify-center p-16">
                    <Loader2Icon className="size-6 animate-spin text-muted-foreground" />
                </div>
            }>
                <TabsContent value="Bank Reconciliation Statement" className="flex min-h-0 flex-col">
                    <BankReconciliationStatement />
                </TabsContent>
                <TabsContent value="Bank Transactions" className="flex min-h-0 flex-col">
                    <BankTransactions />
                </TabsContent>
                <TabsContent value="Bank Clearance Summary" className="flex min-h-0 flex-col">
                    <BankClearanceSummary />
                </TabsContent>
                <TabsContent value="Incorrectly Cleared Entries" className="flex min-h-0 flex-col">
                    <IncorrectlyClearedEntries />
                </TabsContent>
            </Suspense>
        </>}
    </Tabs>
}

export default BankReconciliation