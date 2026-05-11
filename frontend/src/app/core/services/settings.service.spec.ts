import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { BehaviorSubject } from 'rxjs';
import { SettingsService } from './settings.service';
import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';

describe('SettingsService', () => {
  let authState$: BehaviorSubject<boolean>;
  let authServiceMock: any;
  let httpTestingController: HttpTestingController;

  beforeEach(() => {
    TestBed.resetTestingModule();
    localStorage.clear();
    authState$ = new BehaviorSubject<boolean>(false);
    authServiceMock = {
      isLoggedIn: vi.fn(() => authState$.value),
      isLoggedIn$: vi.fn(() => authState$.asObservable())
    };

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        SettingsService,
        { provide: AuthService, useValue: authServiceMock }
      ]
    });

    httpTestingController = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTestingController.verify();
    localStorage.clear();
  });

  it('does not request store settings before authentication', () => {
    TestBed.inject(SettingsService);

    httpTestingController.expectNone(`${environment.apiUrl}/inventory-settings/store`);
  });

  it('loads store settings after authentication becomes available', () => {
    const service = TestBed.inject(SettingsService);
    let storeSettings: any = 'unset';
    service.storeSettings$.subscribe(settings => storeSettings = settings);

    authState$.next(true);

    const req = httpTestingController.expectOne(`${environment.apiUrl}/inventory-settings/store`);
    expect(req.request.method).toBe('GET');
    req.flush({ id: 1, low_stock_quantity_default: 10 });

    expect(storeSettings).toEqual({ id: 1, low_stock_quantity_default: 10 });
  });
});
