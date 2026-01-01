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
  templateUrl: './campaign-calendar.component.html',
  styleUrls: ['./campaign-calendar.component.scss']
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
