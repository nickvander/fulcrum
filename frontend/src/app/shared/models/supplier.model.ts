export interface Supplier {
    id: number;
    name: string;
    contact_person?: string;
    email?: string;
    phone?: string;

    // Address
    address_street?: string;
    address_city?: string;
    address_state?: string;
    address_zip?: string;
    address_country?: string;

    // Financials
    tax_id?: string;
    payment_terms?: string;
    currency?: string;

    // Details
    website?: string;
    internal_notes?: string;
}

export interface SupplierCreate {
    name: string;
    contact_person?: string;
    email?: string;
    phone?: string;
    currency?: string;
    // ... other fields optional
}
