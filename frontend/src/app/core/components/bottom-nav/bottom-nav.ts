import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { TranslocoModule } from '@ngneat/transloco';

interface TabItem {
  labelKey: string;
  icon: string;
  route: string;
  exact?: boolean;
}

/**
 * Mobile bottom-tab bar: the four highest-frequency daily journeys plus a
 * "Más" overflow menu for the rest of the grouped IA. Rendered only on
 * handset/tablet viewports — the shell (app.component) gates it via
 * ScreenService / BreakpointObserver.
 */
@Component({
  selector: 'app-bottom-nav',
  standalone: true,
  imports: [CommonModule, RouterModule, MatIconModule, MatMenuModule, TranslocoModule],
  templateUrl: './bottom-nav.html',
  styleUrls: ['./bottom-nav.scss'],
})
export class BottomNav {
  /** 4 highest-frequency journeys (daily money actions lead). */
  primary: TabItem[] = [
    { labelKey: 'nav.dashboard', icon: 'dashboard', route: '/dashboard' },
    { labelKey: 'nav.sendToMlFull', icon: 'local_shipping', route: '/marketplaces/transfers' },
    { labelKey: 'nav.buyerQuestionsShort', icon: 'forum', route: '/reports/qa' },
    { labelKey: 'nav.expensesShort', icon: 'payments', route: '/expenses' },
  ];

  /** Everything else, reachable via the Más overflow. */
  overflow: TabItem[] = [
    { labelKey: 'nav.orders', icon: 'receipt_long', route: '/orders' },
    { labelKey: 'nav.products', icon: 'inventory_2', route: '/products' },
    { labelKey: 'nav.inventoryAudit', icon: 'history', route: '/products/audit' },
    { labelKey: 'nav.inventoryCount', icon: 'fact_check', route: '/inventory/count' },
    { labelKey: 'nav.alerts', icon: 'notifications_active', route: '/alerts' },
    { labelKey: 'nav.payments', icon: 'payments', route: '/payments' },
    { labelKey: 'nav.suppliers', icon: 'groups', route: '/suppliers' },
    { labelKey: 'nav.purchaseOrders', icon: 'list_alt', route: '/suppliers/po' },
    { labelKey: 'nav.marketplaceChannels', icon: 'store', route: '/marketplaces' },
    { labelKey: 'nav.marketplaceHealth', icon: 'monitor_heart', route: '/marketplaces/health' },
    { labelKey: 'nav.marketing', icon: 'campaign', route: '/marketing' },
    { labelKey: 'nav.users', icon: 'people', route: '/users' },
    { labelKey: 'nav.settings', icon: 'settings', route: '/settings' },
  ];
}
