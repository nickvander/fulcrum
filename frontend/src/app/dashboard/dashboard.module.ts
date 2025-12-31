import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardRoutingModule } from './dashboard-routing.module';
import { DashboardComponent } from './pages/dashboard/dashboard.component';
import { LowStockListWidgetComponent } from './widgets/low-stock-list/low-stock-list.component';
import { InventoryHealthWidgetComponent } from './widgets/inventory-health-widget/inventory-health-widget.component';
import { SharedModule } from '../shared/shared-module';

@NgModule({
    declarations: [],
    imports: [
        CommonModule,
        DashboardRoutingModule,
        DashboardComponent,
        LowStockListWidgetComponent,
        InventoryHealthWidgetComponent,
        SharedModule
    ]
})
export class DashboardModule { }
