import { Component } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Observable } from 'rxjs';
import { map, shareReplay, filter } from 'rxjs/operators';
import { Router, NavigationEnd } from '@angular/router';
import { AsyncPipe, NgIf } from '@angular/common';
import { MatSidenavModule } from '@angular/material/sidenav';
import { RouterModule } from '@angular/router';
import { CoreModule } from './core/core-module';
import { LoadingService } from './core/services/loading.service';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    AsyncPipe,
    NgIf,
    MatSidenavModule,
    RouterModule,
    CoreModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  isHandset$: Observable<boolean>;
  isLoginPage = false;
  loading$: Observable<boolean>;

  constructor(
    private breakpointObserver: BreakpointObserver,
    private router: Router,
    private loadingService: LoadingService
  ) {
    this.isHandset$ = this.breakpointObserver.observe(Breakpoints.Handset)
      .pipe(
        map(result => result.matches),
        shareReplay()
      );

    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe(event => {
      this.isLoginPage = (event as NavigationEnd).url === '/login';
    });

    this.loading$ = this.loadingService.loading$;
  }
}
