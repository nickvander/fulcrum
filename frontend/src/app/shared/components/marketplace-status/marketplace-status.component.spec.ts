
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MarketplaceStatusComponent } from './marketplace-status.component';

describe('MarketplaceStatusComponent', () => {
    let component: MarketplaceStatusComponent;
    let fixture: ComponentFixture<MarketplaceStatusComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [MarketplaceStatusComponent]
        }).compileComponents();

        fixture = TestBed.createComponent(MarketplaceStatusComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
