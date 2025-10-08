import { TestBed } from '@angular/core/testing';
import { Login } from './login';
import { RouterTestingModule } from '@angular/router/testing';

describe('Login', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Login, RouterTestingModule],
    }).compileComponents();
  });

  it('should create the component', () => {
    const fixture = TestBed.createComponent(Login);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});
