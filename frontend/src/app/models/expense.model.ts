export interface Expense {
    id: number;
    description: string;
    amount: number;
    currency: string;
    category: string;
    date: string;
    product_id?: number;
    supplier_id?: number;
    purchase_order_id?: number;
    created_at?: string;
    updated_at?: string;
}

export interface ExpenseCreate extends Omit<Expense, 'id' | 'created_at' | 'updated_at'> { }
export interface ExpenseUpdate extends Partial<ExpenseCreate> { }
