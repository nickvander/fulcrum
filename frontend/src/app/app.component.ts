import { Component } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Observable } from 'rxjs';
import { map, shareReplay, filter, delay } from 'rxjs/operators';

import { Router, NavigationEnd } from '@angular/router';
import { AsyncPipe } from '@angular/common';
import { MatSidenavModule } from '@angular/material/sidenav';
import { RouterModule } from '@angular/router';
import { CoreModule } from './core/core-module';
import { LoadingService } from './core/services/loading.service';
import { ScreenService } from './core/services/screen.service';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    AsyncPipe,
    MatSidenavModule,
    RouterModule,
    CoreModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  isMobile$: Observable<boolean>;
  isLoginPage = false;
  loading$: Observable<boolean>;

  constructor(
    private router: Router,
    private loadingService: LoadingService,
    private screenService: ScreenService
  ) {
    this.isMobile$ = this.screenService.isMobile$;

    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe(event => {
      this.isLoginPage = (event as NavigationEnd).url === '/login';
    });

    this.loading$ = this.loadingService.loading$.pipe(delay(0));
  }
}
