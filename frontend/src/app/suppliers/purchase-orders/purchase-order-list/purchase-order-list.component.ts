import { Component, OnInit, OnDestroy, AfterViewInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PurchaseOrder, PurchaseOrderStatus } from '../../../shared/models/purchase-order.model';
import { Supplier } from '../../../shared/models/supplier.model';
import { SuppliersService } from '../../suppliers.service';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { Subject, takeUntil, forkJoin } from 'rxjs';
import { DateRangeService, DateRange } from '../../../shared/services/date-range.service';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatCardModule } from '@angular/material/card';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { DateRangePresetsComponent } from '../../../shared/components/date-range-presets/date-range-presets.component';
import { StatCardComponent } from '../../../dashboard/widgets/stat-card/stat-card.component';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';

interface POSummary {
  total_orders: number;
  pending_count: number;
  total_value: number;
  received_value: number;
}

@Component({
  selector: 'app-purchase-order-list',
  templateUrl: './purchase-order-list.component.html',
  styleUrls: ['./purchase-order-list.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCardModule,
    MatTooltipModule,
    MatProgressBarModule,
    MatDialogModule,
    DateRangePresetsComponent,
    StatCardComponent,
    TranslocoModule
  ]
})
export class PurchaseOrderListComponent implements OnInit, OnDestroy, AfterViewInit {
  // Data Source for MatTable with sorting
  dataSource = new MatTableDataSource<PurchaseOrder>([]);
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatPaginator) paginator!: MatPaginator;

  purchaseOrders: PurchaseOrder[] = [];
  filteredOrders: PurchaseOrder[] = [];
  suppliers: Supplier[] = [];
  supplierMap: Map<number, Supplier> = new Map();
  displayedColumns: string[] = ['id', 'supplier', 'status', 'total', 'created_at', 'actions'];
  isLoading = false;
  summary: POSummary = { total_orders: 0, pending_count: 0, total_value: 0, received_value: 0 };

  // Filters
  selectedStatus: string = '';
  selectedSupplierId: number | null = null;
  selectedSupplierName: string = 'All Suppliers';
  statusOptions = Object.values(PurchaseOrderStatus);
  startDate: Date | null = null;
  endDate: Date | null = null;

  private destroy$ = new Subject<void>();
  currentLang: string;

  constructor(
    private suppliersService: SuppliersService,
    private router: Router,
    private route: ActivatedRoute,
    private dateRangeService: DateRangeService,
    private translocoService: TranslocoService,
    private dialog: MatDialog
  ) {
    this.currentLang = this.translocoService.getActiveLang();
  }

  ngOnInit(): void {
    // Subscribe to language changes for date pipe
    this.translocoService.langChanges$.pipe(takeUntil(this.destroy$)).subscribe(lang => {
      this.currentLang = lang;
    });

    // Initialize date range from service's current value
    const currentRange = this.dateRangeService.currentRange;
    // ... (rest of ngOnInit)
    this.startDate = currentRange.startDate;
    this.endDate = currentRange.endDate;

    this.loadData();

    // Subscribe to future global date range changes
    this.dateRangeService.dateRange$
      .pipe(takeUntil(this.destroy$))
      .subscribe(range => {
        if (this.purchaseOrders.length > 0) {
          this.startDate = range.startDate;
          this.endDate = range.endDate;
          this.applyFilters();
        }
      });

    // Handle query params for initial supplier filter
    this.route.queryParams
      .pipe(takeUntil(this.destroy$))
      .subscribe(params => {
        if (params['supplier']) {
          this.selectedSupplierId = Number(params['supplier']);
          // If data already loaded, apply filters
          if (this.purchaseOrders.length > 0) {
            this.updateSupplierName();
            this.applyFilters();
          }
        }
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  ngAfterViewInit() {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  loadData(): void {
    this.isLoading = true;
    // Load both POs and suppliers in parallel
    forkJoin({
      pos: this.suppliersService.getPurchaseOrders(),
      suppliers: this.suppliersService.getSuppliers()
    }).subscribe({
      next: ({ pos, suppliers }) => {
        this.suppliers = suppliers;
        this.supplierMap = new Map(suppliers.map(s => [s.id, s]));
        this.purchaseOrders = pos;

        // Update supplier name if ID was set from query params
        if (this.selectedSupplierId) {
          this.updateSupplierName();
        }

        this.applyFilters();
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
      }
    });
  }

  updateSupplierName(): void {
    if (this.selectedSupplierId) {
      const supplier = this.supplierMap.get(this.selectedSupplierId);
      this.selectedSupplierName = supplier ? supplier.name : `Supplier ${this.selectedSupplierId}`;
    } else {
      this.selectedSupplierName = 'All Suppliers';
    }
  }

  getSupplierName(supplierId: number): string {
    const supplier = this.supplierMap.get(supplierId);
    return supplier?.name || `Supplier ${supplierId}`;
  }

  applyFilters(): void {
    let filtered = [...this.purchaseOrders];

    // Status filter
    if (this.selectedStatus) {
      filtered = filtered.filter(po => po.status === this.selectedStatus);
    }

    // Supplier filter
    if (this.selectedSupplierId) {
      filtered = filtered.filter(po => po.supplier_id === this.selectedSupplierId);
    }

    // Date range filter
    if (this.startDate && this.endDate) {
      const startStr = this.dateRangeService.formatDateForApi(this.startDate);
      const endStr = this.dateRangeService.formatDateForApi(this.endDate);

      filtered = filtered.filter(po => {
        // Convert UTC timestamp to local date
        const poLocalDate = this.getLocalDateString(po.created_at);
        return poLocalDate && poLocalDate >= startStr && poLocalDate <= endStr;
      });
    }

    this.filteredOrders = filtered;
    this.dataSource.data = filtered;
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;  // Ensure paginator is linked

    // Custom sorting for nested/calculated properties
    this.dataSource.sortingDataAccessor = (item, property) => {
      switch (property) {
        case 'supplier': return this.getSupplierName(item.supplier_id);
        case 'total': return item.total_amount || 0;
        default: return (item as any)[property];
      }
    };

    this.calculateSummary();
  }

  /** Convert UTC timestamp to local YYYY-MM-DD */
  getLocalDateString(utcTimestamp: string | undefined): string | null {
    if (!utcTimestamp) return null;
    const date = new Date(utcTimestamp);
    return date.toLocaleDateString('en-CA'); // 'en-CA' gives YYYY-MM-DD format
  }

  onFilterChange(): void {
    // Check if supplier name corresponds to "All Suppliers" or a specific one
    // This is handled via UI binding usually, but if using a select:
    // When clearing selection, set selectedSupplierId to null
    this.updateSupplierName();
    this.applyFilters();
  }

  onSupplierFilterChange(supplierId: number | null): void {
    this.selectedSupplierId = supplierId;
    this.updateSupplierName();
    this.applyFilters();
  }

  onDateRangeChange(range: DateRange | null): void {
    this.startDate = range?.startDate || null;
    this.endDate = range?.endDate || null;
    this.applyFilters();
  }

  calculateSummary(): void {
    this.summary.total_orders = this.filteredOrders.length;
    this.summary.pending_count = this.filteredOrders.filter(
      po => po.status === PurchaseOrderStatus.DRAFT || po.status === PurchaseOrderStatus.ORDERED
    ).length;
    this.summary.total_value = this.filteredOrders.reduce(
      (sum, po) => sum + (po.total_amount || 0), 0
    );
    this.summary.received_value = this.filteredOrders
      .filter(po => po.status === PurchaseOrderStatus.COMPLETED)
      .reduce((sum, po) => sum + (po.total_amount || 0), 0);
  }

  createPurchaseOrder(): void {
    this.router.navigate(['/suppliers/po/create']);
  }

  viewDetail(id: number): void {
    this.router.navigate(['/suppliers/po', id]);
  }

  createSupplier(): void {
    this.router.navigate(['/suppliers/id/new']);
  }

  openIngestDialog(): void {
    import('../po-ingest-dialog/po-ingest-dialog.component').then(m => {
      const dialogRef = this.dialog.open(m.PoIngestDialogComponent, {
        width: '800px',
        maxHeight: '90vh',
        disableClose: true
      });

      dialogRef.afterClosed().subscribe(result => {
        if (result?.action === 'created') {
          // Reload data to show the new PO
          this.loadData();
        }
      });
    });
  }

  getStatusColor(status: PurchaseOrderStatus): string {
    const colors: { [key: string]: string } = {
      [PurchaseOrderStatus.DRAFT]: '#9e9e9e',
      [PurchaseOrderStatus.ORDERED]: '#ff9800',
      [PurchaseOrderStatus.PARTIALLY_RECEIVED]: '#2196f3',
      [PurchaseOrderStatus.COMPLETED]: '#4caf50',
      [PurchaseOrderStatus.CLOSED]: '#607d8b'
    };
    return colors[status] || '#9e9e9e';
  }

  getTotalValueFormatted(): string {
    return this.summary.total_value.toFixed(2);
  }

  getReceivedValueFormatted(): string {
    return this.summary.received_value.toFixed(2);
  }

  getStatusTranslationKey(status: string): string {
    // Convert 'Partially_received' or 'PARTIALLY_RECEIVED' to 'partiallyReceived'
    // and lowerCamelCase for others.
    if (!status) return '';

    // Handle specific case for partially received if needed or generic camelCase
    const camelCaseStatus = status.toLowerCase().replace(/_([a-z])/g, (g) => g[1].toUpperCase());
    return `purchaseOrders.${camelCaseStatus}`;
  }
}
