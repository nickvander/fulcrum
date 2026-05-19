import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { of, throwError } from 'rxjs';
import { ActivatedRoute } from '@angular/router';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { MarketplaceDetailComponent } from './marketplace-detail';
import { Marketplace, MarketplacesService } from '../../marketplaces';

describe('MarketplaceDetailComponent', () => {
  let component: MarketplaceDetailComponent;
  let fixture: ComponentFixture<MarketplaceDetailComponent>;
  let serviceStub: {
    getMarketplaceListings: ReturnType<typeof vi.fn>;
    getCredentialForMarketplace: ReturnType<typeof vi.fn>;
    disconnectCredential: ReturnType<typeof vi.fn>;
    getMarketplaceById: ReturnType<typeof vi.fn>;
    updateFeeConfig: ReturnType<typeof vi.fn>;
    recomputeCostBreakdowns: ReturnType<typeof vi.fn>;
  };

  function mkMarketplace(overrides: Partial<Marketplace> = {}): Marketplace {
    return {
      id: 1, name: 'Amazon', api_base_url: 'https://example.com',
      default_fee_rate: 0.15,
      default_shipping_cost: 5.5,
      ...overrides,
    };
  }

  beforeEach(async () => {
    serviceStub = {
      getMarketplaceListings: vi.fn().mockReturnValue(of([])),
      getCredentialForMarketplace: vi.fn().mockReturnValue(of(null)),
      disconnectCredential: vi.fn().mockReturnValue(of({})),
      getMarketplaceById: vi.fn().mockReturnValue(of(mkMarketplace())),
      updateFeeConfig: vi.fn().mockReturnValue(of(mkMarketplace())),
      recomputeCostBreakdowns: vi.fn().mockReturnValue(of({
        breakdowns_created: 2, breakdowns_updated: 5, errors: 0,
      })),
    };

    await TestBed.configureTestingModule({
      imports: [
        MarketplaceDetailComponent,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: MarketplacesService, useValue: serviceStub },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => '1' } } },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(MarketplaceDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // ---------------- Fee config form ----------------

  it('loads the marketplace on init and converts the fractional fee rate into a percent for the form', () => {
    expect(serviceStub.getMarketplaceById).toHaveBeenCalledWith(1);
    // Fraction 0.15 → 15 in the form.
    expect(component.feeRatePercent).toBe(15);
    expect(component.shippingCost).toBe(5.5);
    expect(component.marketplace?.id).toBe(1);
  });

  it('renders the fee-config card once the marketplace is loaded', () => {
    const card = fixture.debugElement.query(By.css('[data-testid="fee-config-card"]'));
    expect(card).not.toBeNull();
  });

  it('saveFeeConfig() PATCHes the percent value converted back to a fraction', () => {
    component.feeRatePercent = 12.5;
    component.shippingCost = 8;
    component.saveFeeConfig();
    expect(serviceStub.updateFeeConfig).toHaveBeenCalledWith(1, {
      default_fee_rate: 0.125,
      default_shipping_cost: 8,
    });
  });

  it('saveFeeConfig() refuses negative inputs without calling the service', () => {
    component.feeRatePercent = -5;
    component.saveFeeConfig();
    expect(serviceStub.updateFeeConfig).not.toHaveBeenCalled();
  });

  it('saveFeeConfig() does nothing while a save is already in flight', () => {
    component.savingFeeConfig = true;
    component.saveFeeConfig();
    expect(serviceStub.updateFeeConfig).not.toHaveBeenCalled();
  });

  it('recomputeBreakdowns() calls the service, records the result, and exposes it to the UI', () => {
    component.recomputeBreakdowns();
    expect(serviceStub.recomputeCostBreakdowns).toHaveBeenCalledWith(1);
    expect(component.recomputeResult).toEqual({
      breakdowns_created: 2, breakdowns_updated: 5, errors: 0,
    });

    fixture.detectChanges();
    const result = fixture.debugElement.query(By.css('[data-testid="recompute-result"]'));
    expect(result).not.toBeNull();
  });

  it('recomputeBreakdowns() does nothing while a recompute is already in flight', () => {
    component.recomputing = true;
    component.recomputeBreakdowns();
    expect(serviceStub.recomputeCostBreakdowns).not.toHaveBeenCalled();
  });

  it('a failing recompute leaves the result null without crashing', () => {
    serviceStub.recomputeCostBreakdowns.mockReturnValueOnce(
      throwError(() => new Error('boom')),
    );
    component.recomputeBreakdowns();
    expect(component.recomputeResult).toBeNull();
    expect(component.recomputing).toBe(false);
  });

  it('if the marketplace fails to load, the fee-config card stays hidden but the page still renders', () => {
    serviceStub.getMarketplaceById.mockReturnValue(throwError(() => new Error('boom')));
    const fresh = TestBed.createComponent(MarketplaceDetailComponent);
    fresh.detectChanges();
    expect(
      fresh.debugElement.query(By.css('[data-testid="fee-config-card"]')),
    ).toBeNull();
    expect(fresh.componentInstance.marketplace).toBeNull();
  });
});
