
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ForcePasswordChangeComponent } from './force-password-change.component';
import { UserService } from '../../services/user.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';

describe('ForcePasswordChangeComponent', () => {
    let component: ForcePasswordChangeComponent;
    let fixture: ComponentFixture<ForcePasswordChangeComponent>;
    let userServiceMock: any;
    let snackBarMock: any;
    let routerMock: any;

    beforeEach(async () => {
        userServiceMock = {
            changePassword: vi.fn()
        };
        snackBarMock = {
            open: vi.fn()
        };

        await TestBed.configureTestingModule({
            imports: [ForcePasswordChangeComponent, NoopAnimationsModule],
            providers: [
                { provide: UserService, useValue: userServiceMock },
                { provide: MatSnackBar, useValue: snackBarMock },
                provideRouter([])
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(ForcePasswordChangeComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
