import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MarketplaceListComponent } from './marketplace-list';
import { MarketplacesService } from '../../marketplaces';
import { of } from 'rxjs';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('MarketplaceListComponent', () => {
  let component: MarketplaceListComponent;
  let fixture: ComponentFixture<MarketplaceListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        MarketplaceListComponent,
        MatSnackBarModule,
        NoopAnimationsModule
      ],
      providers: [
        {
          provide: MarketplacesService,
          useValue: {
            getMarketplaces: () => of([])
          }
        }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(MarketplaceListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
