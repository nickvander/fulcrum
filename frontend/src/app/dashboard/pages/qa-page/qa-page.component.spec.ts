import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import { QaPageComponent } from './qa-page.component';
import {
  AnalyticsReportsService,
  QuestionRow,
  QuestionsListResponse,
} from '../../services/analytics-reports.service';

function makeRow(over: Partial<QuestionRow> = {}): QuestionRow {
  return {
    id: 1, external_question_id: 'Q1', source: 'MERCADOLIBRE',
    item_id: 'MLM1', buyer_id: '555', question_text: '¿Envío a MTY?',
    answer_text: null, status: 'UNANSWERED', asked_at: '2026-03-01T10:00:00Z',
    answered_at: null, answered: false, hours_open: 5, sla_status: 'pending',
    ...over,
  };
}

describe('QaPageComponent', () => {
  let fixture: ComponentFixture<QaPageComponent>;
  let component: QaPageComponent;
  let analyticsStub: { questionsList: ReturnType<typeof vi.fn> };

  function setResponse(rows: QuestionRow[], over: Partial<QuestionsListResponse> = {}): void {
    analyticsStub.questionsList.mockReturnValue(of({
      rows, total: rows.length, sla_hours: 24,
      unanswered_count: rows.filter(r => !r.answered).length,
      breached_count: rows.filter(r => r.sla_status === 'breached').length,
      answered_count: rows.filter(r => r.answered).length,
      ...over,
    } as QuestionsListResponse));
  }

  beforeEach(async () => {
    analyticsStub = {
      questionsList: vi.fn().mockReturnValue(of({
        rows: [], total: 0, sla_hours: 24,
        unanswered_count: 0, breached_count: 0, answered_count: 0,
      } as QuestionsListResponse)),
    };

    await TestBed.configureTestingModule({
      imports: [
        QaPageComponent,
        NoopAnimationsModule,
        RouterTestingModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' },
        }),
      ],
      providers: [
        { provide: AnalyticsReportsService, useValue: analyticsStub },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(QaPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('fetches on init with the 30d default + no status filter', () => {
    expect(analyticsStub.questionsList).toHaveBeenCalledWith(30, 0, 50, undefined);
  });

  it('passes the status filter through when set', () => {
    analyticsStub.questionsList.mockClear();
    component.statusFilter = 'unanswered';
    component.onFilterChange();
    expect(analyticsStub.questionsList).toHaveBeenCalledWith(30, 0, 50, 'unanswered');
  });

  it('surfaces the SLA counters from the response', () => {
    setResponse(
      [makeRow({ id: 1, sla_status: 'breached', answered: false }),
       makeRow({ id: 2, sla_status: 'answered', answered: true })],
      { unanswered_count: 1, breached_count: 1, answered_count: 1, total: 2 },
    );
    component.load();
    expect(component.breachedCount).toBe(1);
    expect(component.answeredCount).toBe(1);
    expect(component.unansweredCount).toBe(1);
  });

  it('resets pageIndex to 0 when the filter changes', () => {
    component.pageIndex = 3;
    component.statusFilter = 'answered';
    component.onFilterChange();
    expect(component.pageIndex).toBe(0);
  });

  it('slaClass maps each status to its pill class', () => {
    expect(component.slaClass('breached')).toBe('sla-breached');
    expect(component.slaClass('answered')).toBe('sla-answered');
    expect(component.slaClass('pending')).toBe('sla-pending');
  });

  it('hoursLabel renders compact h/d', () => {
    expect(component.hoursLabel(null)).toBe('—');
    expect(component.hoursLabel(5)).toBe('5h');
    expect(component.hoursLabel(48)).toBe('2d');
  });

  it('sets errored on failure without throwing', () => {
    analyticsStub.questionsList.mockReturnValue(throwError(() => new Error('boom')));
    component.load();
    expect(component.errored).toBe(true);
    expect(component.rows).toEqual([]);
  });
});
