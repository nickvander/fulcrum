import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MaterialModule } from '../../material.module';

@Component({
  selector: 'app-loading-spinner',
  standalone: true,
  imports: [CommonModule, MaterialModule],
  templateUrl: './loading-spinner.component.html',
  styleUrls: ['./loading-spinner.component.scss']
})
export class LoadingSpinnerComponent {
  @Input() mode: 'determinate' | 'indeterminate' = 'indeterminate';
  @Input() diameter: number = 40;
  @Input() strokeWidth: number = 4;
  @Input() value: number = 0;
  @Input() message: string = '';
  @Input() overlay: boolean = false;
}
