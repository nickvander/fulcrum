import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { DragDropModule, CdkDragDrop, transferArrayItem } from '@angular/cdk/drag-drop';

import { MarketingService, CampaignEvent } from '../../services/marketing.service';

interface CalendarDay {
  id: string; // unique ID for drag-drop connection
  date: Date;
  isCurrentMonth: boolean;
  isToday: boolean;
  events: CampaignEvent[];
}

@Component({
  selector: 'app-campaign-calendar',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatButtonToggleModule,
    MatTooltipModule,
    MatChipsModule,
    MatSnackBarModule,
    DragDropModule
  ],
  template: `
    <div class="calendar-container">
      <!-- Header -->
      <div class="calendar-header">
        <div class="header-left">
          <button mat-icon-button routerLink="/marketing">
            <mat-icon>arrow_back</mat-icon>
          </button>
          <h1>Marketing Calendar</h1>
        </div>
        <div class="header-center">
          <button mat-icon-button (click)="previousMonth()">
            <mat-icon>chevron_left</mat-icon>
          </button>
          <span class="current-month">{{ currentDate | date:'MMMM yyyy' }}</span>
          <button mat-icon-button (click)="nextMonth()">
            <mat-icon>chevron_right</mat-icon>
          </button>
        </div>
        <div class="header-right">
          <button mat-stroked-button (click)="goToToday()">Today</button>
          <button mat-raised-button color="primary" routerLink="/marketing/campaigns/new">
            <mat-icon>add</mat-icon>
            New Campaign
          </button>
        </div>
      </div>

      <!-- Calendar Grid -->
      <mat-card class="calendar-card">
        <!-- Day Headers -->
        <div class="weekday-header">
          <div class="weekday" *ngFor="let day of weekdays">{{ day }}</div>
        </div>

        <!-- Calendar Days -->
        <div class="calendar-grid" cdkDropListGroup>
          <div 
            class="calendar-day" 
            *ngFor="let day of calendarDays"
            [class.other-month]="!day.isCurrentMonth"
            [class.today]="day.isToday"
            cdkDropList
            [cdkDropListData]="day.events"
            (cdkDropListDropped)="onEventDrop($event, day)">
            
            <span class="day-number">{{ day.date | date:'d' }}</span>
            
            <div class="day-events">
              <div 
                class="event-chip" 
                *ngFor="let event of day.events"
                cdkDrag
                [cdkDragData]="event"
                [class]="'status-' + event.status"
                [matTooltip]="event.name + ' (' + event.channel_type + ')'">
                <mat-icon class="channel-icon">{{ getChannelIcon(event.channel_type) }}</mat-icon>
                <span class="event-name">{{ event.name }}</span>
              </div>
            </div>
          </div>
        </div>
      </mat-card>

      <!-- Legend -->
      <div class="calendar-legend">
        <span class="legend-item">
          <span class="legend-dot status-draft"></span> Draft
        </span>
        <span class="legend-item">
          <span class="legend-dot status-scheduled"></span> Scheduled
        </span>
        <span class="legend-item">
          <span class="legend-dot status-published"></span> Published
        </span>
        <span class="legend-item">
          <span class="legend-dot status-failed"></span> Failed
        </span>
      </div>
    </div>
  `,
  styles: [`
    .calendar-container {
      padding: 24px;
      max-width: 1200px;
      margin: 0 auto;
    }

    .calendar-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }

    .header-left, .header-center, .header-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .header-center {
      min-width: 250px;
      justify-content: center;
    }

    .current-month {
      font-size: 18px;
      font-weight: 500;
      min-width: 150px;
      text-align: center;
    }

    .calendar-card {
      border-radius: 12px;
      overflow: hidden;
      padding: 0; 
    }

    .weekday-header {
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      background: #f5f5f5;
      border-bottom: 1px solid #e0e0e0;
    }

    .weekday {
      padding: 12px;
      text-align: center;
      font-weight: 600;
      color: #666;
    }

    .calendar-grid {
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      /* Force equal row heights or auto */
    }

    .calendar-day {
      min-height: 120px;
      padding: 8px;
      border-right: 1px solid #e0e0e0;
      border-bottom: 1px solid #e0e0e0;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .calendar-day:nth-child(7n) {
      border-right: none;
    }

    .calendar-day.other-month {
      background: #fafafa;
      color: #bbb;
    }

    .calendar-day.today {
      background: #e3f2fd;
    }

    .calendar-day.today .day-number {
      background: #1976d2;
      color: white;
      border-radius: 50%;
      width: 24px;
      height: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .day-number {
      font-weight: 500;
      margin-bottom: 4px;
      align-self: flex-start;
    }

    .day-events {
      display: flex;
      flex-direction: column;
      gap: 4px;
      flex: 1;
    }

    /* Drag Drop Styles */
    .cdk-drag-preview {
      box-sizing: border-box;
      border-radius: 4px;
      box-shadow: 0 5px 5px -3px rgba(0, 0, 0, 0.2),
                  0 8px 10px 1px rgba(0, 0, 0, 0.14),
                  0 3px 14px 2px rgba(0, 0, 0, 0.12);
    }

    .cdk-drag-placeholder {
      opacity: 0;
    }

    .cdk-drag-animating {
      transition: transform 250ms cubic-bezier(0, 0, 0.2, 1);
    }

    .calendar-day.cdk-drop-list-dragging .event-chip:not(.cdk-drag-placeholder) {
      transition: transform 250ms cubic-bezier(0, 0, 0.2, 1);
    }

    .event-chip {
      font-size: 11px;
      padding: 4px 6px;
      border-radius: 4px;
      cursor: grab;
      display: flex;
      align-items: center;
      gap: 4px;
      overflow: hidden;
      background: white;
      border: 1px solid #ddd;
    }
    
    .event-chip:active {
      cursor: grabbing;
    }

    .channel-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
    }

    .event-name {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .status-draft { border-left: 3px solid #1565c0; }
    .status-scheduled { border-left: 3px solid #e65100; }
    .status-published { border-left: 3px solid #2e7d32; }
    .status-active { border-left: 3px solid #2e7d32; }
    .status-failed { border-left: 3px solid #c62828; }

    .calendar-legend {
      display: flex;
      gap: 24px;
      justify-content: center;
      margin-top: 16px;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
    }

    .legend-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }
    
    .legend-dot.status-draft { background: #1565c0; }
    .legend-dot.status-scheduled { background: #e65100; }
    .legend-dot.status-published { background: #2e7d32; }
    .legend-dot.status-failed { background: #c62828; }
  `]
})
export class CampaignCalendarComponent implements OnInit {
  currentDate = new Date();
  weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  calendarDays: CalendarDay[] = [];
  events: CampaignEvent[] = [];

  constructor(
    private marketingService: MarketingService,
    private snackBar: MatSnackBar
  ) { }

  ngOnInit(): void {
    this.loadEvents();
  }

  loadEvents(): void {
    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();

    // Fetch events for current month (+ padding)
    const start = new Date(year, month - 1, 1).toISOString();
    const end = new Date(year, month + 2, 0).toISOString();

    this.marketingService.getEvents(start, end).subscribe({
      next: (events) => {
        this.events = events;
        this.generateCalendar();
      },
      error: (err) => {
        console.error('Failed to load events', err);
        this.snackBar.open('Failed to load calendar events', 'Close', { duration: 3000 });
        // Still generate calendar grid even if no events
        this.generateCalendar();
      }
    });
  }

  generateCalendar(): void {
    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - startDate.getDay());

    const endDate = new Date(lastDay);
    endDate.setDate(endDate.getDate() + (6 - endDate.getDay()));

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    this.calendarDays = [];
    const current = new Date(startDate);

    while (current <= endDate) {
      const dayDate = new Date(current);
      const dateStr = dayDate.toISOString().split('T')[0];

      const dayEvents = this.events.filter(e => {
        if (!e.scheduled_at) return false;
        return e.scheduled_at.startsWith(dateStr);
      });

      this.calendarDays.push({
        id: `day-${dateStr}`,
        date: dayDate,
        isCurrentMonth: dayDate.getMonth() === month,
        isToday: dayDate.getTime() === today.getTime(),
        events: dayEvents
      });

      current.setDate(current.getDate() + 1);
    }
  }

  onEventDrop(event: CdkDragDrop<CampaignEvent[]>, day: CalendarDay) {
    if (event.previousContainer === event.container) {
      // Reordering in same day - no date change needed usually, unless time changes
      // For now, no-op
    } else {
      // Move to different day
      transferArrayItem(
        event.previousContainer.data,
        event.container.data,
        event.previousIndex,
        event.currentIndex,
      );

      const droppedEvent = event.container.data[event.currentIndex];
      const newDate = new Date(day.date);
      // Preserve time if possible, or set to 9am?
      // Let's assume we keep the time part from original scheduled_at if possible, 
      // but if we dragged to a specific day, we update the DATE part.

      let originalTime = '09:00:00';
      if (droppedEvent.scheduled_at) {
        originalTime = droppedEvent.scheduled_at.split('T')[1]?.split('.')[0] || '09:00:00';
      }

      const newDateIso = newDate.toISOString().split('T')[0];
      const newScheduledAt = `${newDateIso}T${originalTime}`;

      this.marketingService.updateEvent(droppedEvent.id, { scheduled_at: newScheduledAt }).subscribe({
        next: (updated) => {
          droppedEvent.scheduled_at = updated.scheduled_at;
          this.snackBar.open('Event rescheduled', 'Close', { duration: 2000 });
        },
        error: (err) => {
          console.error('Reschedule failed', err);
          this.snackBar.open('Failed to reschedule event', 'Close', { duration: 3000 });
          // Revert UI change? Ideally yes.
          // Reloading events is safest.
          this.loadEvents();
        }
      });
    }
  }

  previousMonth(): void {
    this.currentDate = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() - 1, 1);
    this.loadEvents();
  }

  nextMonth(): void {
    this.currentDate = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() + 1, 1);
    this.loadEvents();
  }

  goToToday(): void {
    this.currentDate = new Date();
    this.loadEvents();
  }

  getChannelIcon(channelType: string): string {
    const icons: Record<string, string> = {
      'email': 'email',
      'social': 'share',
      'paid_ad': 'campaign',
      'facebook': 'thumb_up',
      'instagram': 'camera_alt',
      'tiktok': 'play_circle'
    };
    return icons[channelType] || 'event';
  }
}
