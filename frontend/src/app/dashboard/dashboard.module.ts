import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardRoutingModule } from './dashboard-routing.module';
import { DashboardComponent } from './pages/dashboard/dashboard.component';
import { KpiCardComponent } from './widgets/kpi-card/kpi-card.component';
import { LowStockListWidgetComponent } from './widgets/low-stock-list/low-stock-list.component';
import { SharedModule } from '../shared/shared-module';
import { MatCardModule } from '@angular/material/card';
import { MatGridListModule } from '@angular/material/grid-list';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';

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
