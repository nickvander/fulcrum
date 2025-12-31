import { Component, OnInit, ViewChild, AfterViewInit } from '@angular/core';
import { MatTableDataSource } from '@angular/material/table';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { Router } from '@angular/router';
import { forkJoin } from 'rxjs';
import { SuppliersService } from '../suppliers.service';
import { PurchaseOrder } from '../../shared/models/purchase-order.model';

interface SupplierSummary {
    id: number;
    name: string;
    contact_name?: string;
    email?: string;
    po_count: number;
    total_po_value: number;
}

@Component({
    selector: 'app-supplier-list',
    templateUrl: './supplier-list.component.html',
    styleUrls: ['./supplier-list.component.scss'],
    standalone: false
})
export class SupplierListComponent implements OnInit, AfterViewInit {
    dataSource = new MatTableDataSource<SupplierSummary>([]);

    @ViewChild(MatPaginator) paginator!: MatPaginator;
    // Use setter since table is inside *ngIf
    @ViewChild(MatSort) set matSort(sort: MatSort) {
        if (sort) {
            this.dataSource.sort = sort;
        }
    }

    suppliers: SupplierSummary[] = [];
    displayedColumns: string[] = ['name', 'contact', 'po_count', 'total_value', 'actions'];
    isLoading = false;

    constructor(
        private suppliersService: SuppliersService,
        private router: Router
    ) { }

    ngOnInit(): void {
        this.dataSource.sortingDataAccessor = (item, property) => {
            switch (property) {
                case 'total_value': return item.total_po_value;
                case 'contact': return item.contact_name || '';
                default: return (item as any)[property];
            }
        };
        this.loadData();
    }

    ngAfterViewInit() {
        this.dataSource.paginator = this.paginator;
    }

    loadData(): void {
        this.isLoading = true;
        // Load both suppliers and POs in parallel
        forkJoin({
            suppliers: this.suppliersService.getSuppliers(),
            pos: this.suppliersService.getPurchaseOrders()
        }).subscribe({
            next: ({ suppliers, pos }) => {
                // Group POs by supplier
                const poBySupplier = new Map<number, PurchaseOrder[]>();
                pos.forEach(po => {
                    if (!poBySupplier.has(po.supplier_id)) {
                        poBySupplier.set(po.supplier_id, []);
                    }
                    poBySupplier.get(po.supplier_id)!.push(po);
                });

                // Transform suppliers with calculated PO stats
                this.suppliers = suppliers.map(s => {
                    const supplierPOs = poBySupplier.get(s.id) || [];
                    return {
                        id: s.id,
                        name: s.name,
                        contact_name: s.contact_person,
                        email: s.email,
                        po_count: supplierPOs.length,
                        total_po_value: supplierPOs.reduce((sum, po) => sum + (po.total_amount || 0), 0)
                    };
                });
                this.dataSource.data = this.suppliers;
                // Re-link paginator/sort if needed, but AfterViewInit handles it usually. 
                // However, explicit re-link if data loads after view init is safe.
                if (this.paginator) this.dataSource.paginator = this.paginator;

                this.isLoading = false;
            },
            error: () => {
                this.isLoading = false;
            }
        });
    }

    viewSupplier(id: number): void {
        this.router.navigate(['/suppliers/id', id]);
    }

    createSupplier(): void {
        this.router.navigate(['/suppliers/id/new']);
    }

    viewPurchaseOrders(supplierId: number): void {
        this.router.navigate(['/suppliers/po'], { queryParams: { supplier: supplierId } });
    }
}
