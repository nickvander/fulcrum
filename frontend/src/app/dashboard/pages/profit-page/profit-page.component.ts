import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { TranslocoModule } from '@ngneat/transloco';

import { ProfitSummaryWidgetComponent } from '../../widgets/profit-summary-widget/profit-summary-widget.component';

/**
 * "¿Gané o perdí?" profit page (`/reports/profit`).
 *
 * Full-bleed host for the shared `ProfitSummaryWidgetComponent` (page mode:
 * period selector + breakdown ladder). Mirrors the qa-page / refunds-page
 * lazy route pattern. The dashboard card is a compact embed of the same
 * component.
 */
@Component({
  selector: 'app-profit-page',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatButtonModule,
    MatIconModule,
    TranslocoModule,
    ProfitSummaryWidgetComponent,
  ],
  templateUrl: './profit-page.component.html',
  styleUrls: ['./profit-page.component.scss'],
})
export class ProfitPageComponent {}
