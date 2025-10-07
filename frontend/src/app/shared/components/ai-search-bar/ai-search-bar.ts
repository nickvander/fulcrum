import { Component, EventEmitter, OnDestroy, OnInit, Output } from '@angular/core';
import { FormControl } from '@angular/forms';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-ai-search-bar',
  templateUrl: './ai-search-bar.html',
  styleUrl: './ai-search-bar.scss'
})
export class AiSearchBar implements OnInit, OnDestroy {
  @Output() searchQuery = new EventEmitter<string>();
  searchControl = new FormControl('');
  private destroy$ = new Subject<void>();

  ngOnInit(): void {
    this.searchControl.valueChanges.pipe(
      debounceTime(400),
      distinctUntilChanged(),
      takeUntil(this.destroy$)
    ).subscribe(query => {
      if (query !== null) {
        this.searchQuery.emit(query);
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  startVoiceSearch(): void {
    // TODO: Implement voice recognition using Web Speech API
    console.log('Voice search initiated.');
  }

  clearSearch(): void {
    this.searchControl.setValue('');
  }
}
