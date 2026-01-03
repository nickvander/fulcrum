
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { InventoryHealthWidgetComponent } from './inventory-health-widget.component';
import { ProductService } from '../../../products/services/product';
import { of } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule } from '@angular/router';
import { TranslocoTestingModule } from '@ngneat/transloco';

describe('InventoryHealthWidgetComponent', () => {
    let component: InventoryHealthWidgetComponent;
    let fixture: ComponentFixture<InventoryHealthWidgetComponent>;
    let productServiceMock: any;

    beforeEach(async () => {
        productServiceMock = {
            getProducts: vi.fn().mockReturnValue(of({
                data: [
                    { id: 1, name: 'Low Stock Item', stock_quantity: 5, days_of_inventory: 10 },
                    { id: 2, name: 'Normal Item', stock_quantity: 100, days_of_inventory: 60 }
                ],
                total: 2
            }))
        };

        await TestBed.configureTestingModule({
            imports: [
                InventoryHealthWidgetComponent,
                MatCardModule,
                MatListModule,
                MatIconModule,
                RouterModule.forRoot([]),
                TranslocoTestingModule.forRoot({ langs: { en: {}, 'es-MX': {} } })
            ],
            providers: [
                { provide: ProductService, useValue: productServiceMock }
            ]
        })
            .compileComponents();

        fixture = TestBed.createComponent(InventoryHealthWidgetComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should filter low stock items correctly', () => {
        expect(component.lowStockItems.length).toBe(1);
        expect(component.lowStockItems[0].name).toBe('Low Stock Item');
    });
});
