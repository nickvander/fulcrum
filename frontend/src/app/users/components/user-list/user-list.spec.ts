import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { UserList } from './user-list';
import { UserService } from '../../services/user.service';

describe('UserList', () => {
  let component: UserList;
  let fixture: ComponentFixture<UserList>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserList, HttpClientTestingModule],
      providers: [UserService]
    })
    .compileComponents();

    fixture = TestBed.createComponent(UserList);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
