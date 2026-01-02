import { NgModule, NO_ERRORS_SCHEMA } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatSortModule } from '@angular/material/sort';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatCardModule } from '@angular/material/card';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatDialogModule } from '@angular/material/dialog';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatPaginatorModule } from '@angular/material/paginator'; // Added correct import statement
import { MatSidenavModule } from '@angular/material/sidenav';
import { SupplierDashboardComponent } from './pages/supplier-dashboard/supplier-dashboard.component';
import { ReceivingDialogComponent } from './purchase-orders/receiving-dialog/receiving-dialog.component';
import { QuickProductDialogComponent } from './purchase-orders/quick-product-dialog/quick-product-dialog.component';
import { CostAllocationDialogComponent } from './purchase-orders/cost-allocation-dialog/cost-allocation-dialog.component';
import { SupplierSelectionDialogComponent } from './purchase-orders/supplier-selection-dialog/supplier-selection-dialog.component';
import { UserService } from '../users/services/user.service';
import { MatListModule } from '@angular/material/list';
import { TranslocoModule } from '@ngneat/transloco';

import { SuppliersRoutingModule } from './suppliers-routing.module';
import { SupplierListComponent } from './supplier-list/supplier-list.component';
import { SupplierDetailComponent } from './supplier-detail/supplier-detail.component';
import { PurchaseOrderListComponent } from './purchase-orders/purchase-order-list/purchase-order-list.component';
import { PurchaseOrderEditComponent } from './purchase-orders/purchase-order-edit/purchase-order-edit.component';
import { StatCardComponent } from '../dashboard/widgets/stat-card/stat-card.component';
import { DateRangePresetsComponent } from '../shared/components/date-range-presets/date-range-presets.component';

import { MatTabsModule } from '@angular/material/tabs';
import { SupplierProductManagerComponent } from './supplier-product-manager/supplier-product-manager.component';

@NgModule({
  declarations: [],
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    SuppliersRoutingModule,
    MatTableModule,
    MatSortModule,
    MatButtonModule,
    MatInputModule,
    MatIconModule,
    MatSelectModule,
    MatCardModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatDialogModule,
    MatAutocompleteModule,
    MatTooltipModule,
    MatCheckboxModule,
    MatListModule,
    MatDividerModule,
    MatProgressSpinnerModule,
    MatProgressBarModule,
    MatTabsModule,
    StatCardComponent,
    SupplierProductManagerComponent,
    DateRangePresetsComponent,
    MatPaginatorModule,
    MatSidenavModule,
    SupplierDashboardComponent,
    TranslocoModule,
    SupplierListComponent,
    SupplierDetailComponent,
    SupplierSelectionDialogComponent,
    CostAllocationDialogComponent,
    ReceivingDialogComponent,
    QuickProductDialogComponent,
    PurchaseOrderListComponent,
    PurchaseOrderEditComponent
  ],
  providers: [
    UserService
  ],
  schemas: [NO_ERRORS_SCHEMA]
})
export class SuppliersModule { }
