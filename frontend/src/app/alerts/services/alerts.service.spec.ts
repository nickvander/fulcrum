import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';

import {
  AlertRule,
  AlertRuleCreate,
  AlertsService,
} from './alerts.service';
import { environment } from '../../../environments/environment';

describe('AlertsService', () => {
  let service: AlertsService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [AlertsService],
    });
    service = TestBed.inject(AlertsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('list() GETs /alerts/rules', () => {
    service.list().subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/alerts/rules`);
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });

  it('create() POSTs the payload to /alerts/rules', () => {
    const payload: AlertRuleCreate = {
      alert_type: 'low_margin',
      threshold: 25,
      notify_email: 'ops@example.com',
    };
    service.create(payload).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/alerts/rules`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(payload);
    req.flush({});
  });

  it('update() PATCHes /alerts/rules/{id} with the partial body', () => {
    service.update(7, { enabled: false, threshold: 12 }).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/alerts/rules/7`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ enabled: false, threshold: 12 });
    req.flush({});
  });

  it('delete() DELETEs /alerts/rules/{id}', () => {
    service.delete(3).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/alerts/rules/3`);
    expect(req.request.method).toBe('DELETE');
    req.flush({ deleted: 3 });
  });

  it('test() POSTs /alerts/rules/{id}/test', () => {
    service.test(11).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/alerts/rules/11/test`);
    expect(req.request.method).toBe('POST');
    req.flush({ rule_id: 11, triggered: false, payload: {}, notification_sent: false });
  });

  it('events() GETs /alerts/rules/{id}/events', () => {
    service.events(11).subscribe();
    const req = httpMock.expectOne(`${environment.apiUrl}/alerts/rules/11/events`);
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });
});
