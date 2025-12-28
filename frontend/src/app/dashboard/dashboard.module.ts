import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardRoutingModule } from './dashboard-routing.module';
import { DashboardComponent } from './pages/dashboard/dashboard.component';
import { KpiCardComponent } from './widgets/kpi-card/kpi-card.component';
import { LowStockListWidgetComponent } from './widgets/low-stock-list/low-stock-list.component';
import { SharedModule } from '../shared/shared-module';

@NgModule({
    declarations: [],
    imports: [
        CommonModule,
        DashboardRoutingModule,
        DashboardComponent,
        KpiCardComponent,
        LowStockListWidgetComponent,
        SharedModule
    ]
})
export class DashboardModule { }
