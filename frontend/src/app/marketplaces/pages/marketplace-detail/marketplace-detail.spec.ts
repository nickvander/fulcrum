import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MarketplaceDetailComponent } from './marketplace-detail';
import { MarketplacesService } from '../../marketplaces';
import { of } from 'rxjs';
import { ActivatedRoute } from '@angular/router';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('MarketplaceDetailComponent', () => {
  let component: MarketplaceDetailComponent;
  let fixture: ComponentFixture<MarketplaceDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        MarketplaceDetailComponent,
        NoopAnimationsModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' }
        })
      ],
      providers: [
        {
          provide: MarketplacesService,
          useValue: {
            getMarketplaceListings: () => of([]),
            getCredentialForMarketplace: () => of(null),
            disconnectCredential: () => of({})
          }
        },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { paramMap: { get: () => '1' } }
          }
        }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(MarketplaceDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
