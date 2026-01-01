
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { StatusFilterComponent } from './status-filter.component';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('StatusFilterComponent', () => {
    let component: StatusFilterComponent;
    let fixture: ComponentFixture<StatusFilterComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [StatusFilterComponent, NoopAnimationsModule]
        }).compileComponents();

        fixture = TestBed.createComponent(StatusFilterComponent);
        component = fixture.componentInstance;
        component.options = [{ label: 'Active', value: 'active' }];
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
