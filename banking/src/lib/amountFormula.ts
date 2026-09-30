import { Parser } from 'safe-expr-eval'

const parser = new Parser()

const PLAIN_NUMBER_PATTERN = /^-?\d+(\.\d+)?$/

export function evaluateAmountFormula(expression: string, transactionAmount: number): number {
    const trimmed = expression.trim()
    if (!trimmed) {
        return 0
    }

    if (PLAIN_NUMBER_PATTERN.test(trimmed)) {
        return Number(trimmed)
    }

    try {
        const result = parser.parse(trimmed).evaluate({ transaction_amount: transactionAmount })
        if (typeof result !== 'number' || !Number.isFinite(result)) {
            return 0
        }
        return result
    } catch {
        return 0
    }
}
