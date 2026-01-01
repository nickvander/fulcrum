import { ComponentFixture, TestBed } from '@angular/core/testing';
import { StatCardComponent } from './stat-card.component';
import { RouterTestingModule } from '@angular/router/testing';
import { By } from '@angular/platform-browser';

describe('StatCardComponent', () => {
    let component: StatCardComponent;
    let fixture: ComponentFixture<StatCardComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [StatCardComponent, RouterTestingModule]
        }).compileComponents();

        fixture = TestBed.createComponent(StatCardComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should display title and value', () => {
        component.title = 'Total Profit';
        component.value = '$1,234';
        fixture.detectChanges();

        const label = fixture.debugElement.query(By.css('.kpi-label'));
        const value = fixture.debugElement.query(By.css('.kpi-value'));

        expect(label.nativeElement.textContent).toContain('Total Profit');
        expect(value.nativeElement.textContent).toContain('$1,234');
    });

    it('should apply correct color class', () => {
        component.colorType = 'success';
        fixture.detectChanges();
        const card = fixture.debugElement.query(By.css('.stat-card'));
        expect(card.nativeElement.classList.contains('gradient-success')).toBe(true);
    });
});
