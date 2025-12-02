import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { AuditLogsComponent } from './audit-logs.component';
import { AuditLogService } from '../../services/audit-log.service';

describe('AuditLogsComponent', () => {
  let component: AuditLogsComponent;
  let fixture: ComponentFixture<AuditLogsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AuditLogsComponent, HttpClientTestingModule, NoopAnimationsModule],
      providers: [AuditLogService]
    })
      .compileComponents();

    fixture = TestBed.createComponent(AuditLogsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
