import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslocoTestingModule } from '@ngneat/transloco';
import { of, throwError } from 'rxjs';

import type { MatSnackBar } from '@angular/material/snack-bar';

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
  let analyticsStub: {
    questionsList: ReturnType<typeof vi.fn>;
    answerQuestion: ReturnType<typeof vi.fn>;
  };

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
      answerQuestion: vi.fn(),
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

  // ---- inline answer composer --------------------------------------------

  it('openComposer reveals the composer for one row and resets state', () => {
    const row = makeRow({ id: 7 });
    component.answerErrorRowId = 7;
    component.reauthRowId = 7;
    component.openComposer(row);
    expect(component.composerRowId).toBe(7);
    expect(component.answerText).toBe('');
    expect(component.answerErrorRowId).toBeNull();
    expect(component.reauthRowId).toBeNull();
  });

  it('disables submit when the answer text is empty or whitespace', () => {
    component.openComposer(makeRow({ id: 1 }));
    component.answerText = '   ';
    expect(component.submitDisabled).toBe(true);
    component.answerText = 'Hola';
    expect(component.submitDisabled).toBe(false);
  });

  it('submitAnswer calls the service and patches the row + counters in place', () => {
    const row = makeRow({ id: 3, sla_status: 'breached', answered: false });
    setResponse([row], { unanswered_count: 1, breached_count: 1, answered_count: 0, total: 1 });
    component.load();

    analyticsStub.answerQuestion.mockReturnValue(of(makeRow({
      id: 3, answered: true, answer_text: 'Sí', answered_at: '2026-03-02T00:00:00Z',
      status: 'ANSWERED', sla_status: 'answered', hours_open: 2,
    })));

    component.openComposer(row);
    component.answerText = 'Sí';
    component.submitAnswer(row);

    expect(analyticsStub.answerQuestion).toHaveBeenCalledWith(3, 'Sí');
    expect(row.answered).toBe(true);
    expect(row.answer_text).toBe('Sí');
    expect(row.sla_status).toBe('answered');
    // Counters update without a full reload (load called once on init only).
    expect(component.unansweredCount).toBe(0);
    expect(component.answeredCount).toBe(1);
    expect(component.breachedCount).toBe(0);
    expect(component.composerRowId).toBeNull();
    expect(analyticsStub.questionsList).toHaveBeenCalledTimes(2); // init + the load() above
  });

  it('shows an inline error when the answer submission fails', () => {
    const row = makeRow({ id: 4 });
    analyticsStub.answerQuestion.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 500 })),
    );
    component.openComposer(row);
    component.answerText = 'Hola';
    component.submitAnswer(row);
    expect(component.answerErrorRowId).toBe(4);
    expect(component.reauthRowId).toBeNull();
    expect(row.answered).toBe(false);
  });

  it('flips into the Reconnect state on a 409 needs_reauthorization', () => {
    const row = makeRow({ id: 5 });
    analyticsStub.answerQuestion.mockReturnValue(throwError(() => new HttpErrorResponse({
      status: 409, error: { code: 'needs_reauthorization' },
    })));
    component.openComposer(row);
    component.answerText = 'Hola';
    component.submitAnswer(row);
    expect(component.reauthRowId).toBe(5);
    expect(component.answerErrorRowId).toBeNull();
  });

  it('Ctrl+Enter in the composer submits when the button is enabled', () => {
    const row = makeRow({ id: 8 });
    analyticsStub.answerQuestion.mockReturnValue(of(makeRow({
      id: 8, answered: true, answer_text: 'Sí', sla_status: 'answered',
    })));
    component.openComposer(row);
    component.answerText = 'Sí';

    const event = new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true });
    const prevent = vi.spyOn(event, 'preventDefault');
    component.onComposerKeydown(event, row);

    expect(prevent).toHaveBeenCalled();
    expect(analyticsStub.answerQuestion).toHaveBeenCalledWith(8, 'Sí');
  });

  it('Cmd+Enter also submits the composer', () => {
    const row = makeRow({ id: 9 });
    analyticsStub.answerQuestion.mockReturnValue(of(makeRow({ id: 9, answered: true })));
    component.openComposer(row);
    component.answerText = 'Listo';
    component.onComposerKeydown(
      new KeyboardEvent('keydown', { key: 'Enter', metaKey: true }), row,
    );
    expect(analyticsStub.answerQuestion).toHaveBeenCalledWith(9, 'Listo');
  });

  it('Ctrl+Enter does NOT submit when the answer is empty/whitespace', () => {
    const row = makeRow({ id: 10 });
    component.openComposer(row);
    component.answerText = '   ';
    component.onComposerKeydown(
      new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true }), row,
    );
    expect(analyticsStub.answerQuestion).not.toHaveBeenCalled();
  });

  it('plain Enter does not submit (newline preserved)', () => {
    const row = makeRow({ id: 11 });
    component.openComposer(row);
    component.answerText = 'Hola';
    const event = new KeyboardEvent('keydown', { key: 'Enter' });
    const prevent = vi.spyOn(event, 'preventDefault');
    component.onComposerKeydown(event, row);
    expect(prevent).not.toHaveBeenCalled();
    expect(analyticsStub.answerQuestion).not.toHaveBeenCalled();
  });

  it('removes the answered row from the list when the filter is "unanswered"', () => {
    const r1 = makeRow({ id: 20, answered: false });
    const r2 = makeRow({ id: 21, answered: false });
    component.statusFilter = 'unanswered';
    setResponse([r1, r2], {
      unanswered_count: 2, breached_count: 0, answered_count: 0, total: 2,
    });
    component.load();
    expect(component.rows.length).toBe(2);

    analyticsStub.answerQuestion.mockReturnValue(of(makeRow({
      id: 20, answered: true, answer_text: 'Sí', sla_status: 'answered',
    })));
    component.openComposer(r1);
    component.answerText = 'Sí';
    component.submitAnswer(r1);

    // The just-answered row leaves the unanswered-only list.
    expect(component.rows.map(r => r.id)).toEqual([21]);
    expect(component.totalRows).toBe(1);
    expect(component.unansweredCount).toBe(1);
    expect(component.answeredCount).toBe(1);
  });

  it('keeps the answered row in the list when the filter is "all"', () => {
    const r1 = makeRow({ id: 30, answered: false });
    component.statusFilter = '';
    setResponse([r1], {
      unanswered_count: 1, breached_count: 0, answered_count: 0, total: 1,
    });
    component.load();

    analyticsStub.answerQuestion.mockReturnValue(of(makeRow({
      id: 30, answered: true, answer_text: 'Sí', sla_status: 'answered',
    })));
    component.openComposer(r1);
    component.answerText = 'Sí';
    component.submitAnswer(r1);

    expect(component.rows.map(r => r.id)).toEqual([30]);
    expect(component.rows[0].answered).toBe(true);
    expect(component.totalRows).toBe(1);
  });

  it('shows the already_answered reload path on a 409 alreadyAnswered code', () => {
    const row = makeRow({ id: 40 });
    analyticsStub.answerQuestion.mockReturnValue(throwError(() => new HttpErrorResponse({
      status: 409, error: { code: 'apiErrors.question.alreadyAnswered' },
    })));
    component.openComposer(row);
    component.answerText = 'Hola';
    component.submitAnswer(row);

    expect(component.alreadyAnsweredRowId).toBe(40);
    expect(component.answerErrorRowId).toBeNull();
    expect(component.reauthRowId).toBeNull();
  });

  it('reloadAfterConflict clears the conflict state and refetches', () => {
    component.alreadyAnsweredRowId = 40;
    component.composerRowId = 40;
    analyticsStub.questionsList.mockClear();
    component.reloadAfterConflict();
    expect(component.alreadyAnsweredRowId).toBeNull();
    expect(component.composerRowId).toBeNull();
    expect(analyticsStub.questionsList).toHaveBeenCalledTimes(1);
  });

  it('fires the success snackbar on a successful answer', () => {
    const snackBar = (component as unknown as { snackBar: MatSnackBar }).snackBar;
    const openSpy = vi.spyOn(snackBar, 'open');
    const row = makeRow({ id: 50, answered: false });
    analyticsStub.answerQuestion.mockReturnValue(of(makeRow({
      id: 50, answered: true, answer_text: 'Sí', sla_status: 'answered',
    })));
    component.openComposer(row);
    component.answerText = 'Sí';
    component.submitAnswer(row);

    expect(openSpy).toHaveBeenCalledWith(
      'dashboard.qaPage.answerSuccess', undefined, { duration: 2500 },
    );
  });
});
