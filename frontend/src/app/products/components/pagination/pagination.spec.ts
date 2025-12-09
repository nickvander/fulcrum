import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';
import { PaginationComponent } from './pagination';

describe('PaginationComponent', () => {
    let component: PaginationComponent;
    let fixture: ComponentFixture<PaginationComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [
                MatIconModule,
                MatButtonModule,
                MatInputModule,
                FormsModule,
                PaginationComponent
            ]
        })
            .compileComponents();
    });

    beforeEach(() => {
        fixture = TestBed.createComponent(PaginationComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should display pagination info correctly', () => {
        component.currentPage = 2;
        component.pageSize = 10;
        component.totalItems = 50;
        component.totalPages = 5; // Manually set totalPages as it's an Input
        fixture.detectChanges();

        const paginationInfo = fixture.debugElement.query(By.css('.pagination-text'));
        expect(paginationInfo.nativeElement.textContent.trim()).toContain('Showing 11 - 20 of 50 items');
    });

    it('should emit pageChange event when onPageChange is called', () => {
        vi.spyOn(component.pageChange, 'emit');
        component.totalPages = 5; // Ensure valid page
        component.onPageChange(3);
        expect(component.pageChange.emit).toHaveBeenCalledWith(3);
    });

    it('should emit pageChange event when onNext is called and has next page', () => {
        vi.spyOn(component.pageChange, 'emit');
        component.currentPage = 2;
        component.totalPages = 5;
        component.hasNextPage = true;
        component.onNext();
        expect(component.pageChange.emit).toHaveBeenCalledWith(3);
    });

    it('should emit pageChange event when onPrev is called and has previous page', () => {
        vi.spyOn(component.pageChange, 'emit');
        component.currentPage = 2;
        component.onPrev();
        expect(component.pageChange.emit).toHaveBeenCalledWith(1);
    });

    it('should emit pageSizeChange event when page size is changed', () => {
        vi.spyOn(component.pageSizeChange, 'emit');
        component.pageSize = 25;
        component.onPageSizeChange();
        expect(component.pageSizeChange.emit).toHaveBeenCalledWith(25);
    });

    it('should generate page numbers correctly', () => {
        component.currentPage = 5;
        component.totalPages = 10;
        fixture.detectChanges();

        // Test page numbers are generated properly by checking the component's pages array
        expect(component.pages.length).toBeGreaterThan(0);
    });

    it('should calculate end item correctly', () => {
        component.currentPage = 3;
        component.pageSize = 10;
        component.totalItems = 25;
        const result = component.calculateEndItem();
        expect(result).toBe(25); // Should not exceed totalItems
    });
});
