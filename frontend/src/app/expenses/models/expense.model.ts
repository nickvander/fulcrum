export interface Expense {
    id: number;
    description: string;
    amount: number;
    currency: string;
    category: string;
    is_custom_category: boolean;
    date: string;
    expense_type: 'one_time' | 'recurring';
    recurrence_interval?: 'weekly' | 'monthly' | 'quarterly' | 'yearly';
    reference_number?: string;
    payment_method?: 'cash' | 'card' | 'transfer' | 'check';
    notes?: string;
    // User who paid (for reimbursement tracking)
    paid_by_user_id?: number;
    paid_by_name?: string;
    is_reimbursed?: boolean;
    reimbursed_at?: string;
    // Optional associations
    product_id?: number;
    supplier_id?: number;
    purchase_order_id?: number;
    created_at?: string;
    updated_at?: string;
}

export interface ExpenseCreate extends Omit<Expense, 'id' | 'created_at' | 'updated_at' | 'reimbursed_at'> { }
export interface ExpenseUpdate extends Partial<ExpenseCreate> { }

export interface ExpenseSummary {
    total_amount: number;
    by_category: { [key: string]: number };
    by_type: { one_time: number; recurring: number };
    by_user: { [key: string]: number };
    unreimbursed_total: number;
    count: number;
}


