import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatListModule } from '@angular/material/list';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';
import { ProductTemplateService } from '../services/product-template.service';
import { ProductTemplate } from '../models/product-template.model';

@Component({
  selector: 'app-product-templates',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatListModule,
    MatProgressBarModule,
    RouterLink
  ],
  templateUrl: './product-templates.html',
  styleUrls: ['./product-templates.scss']
})
export class ProductTemplatesComponent implements OnInit {
  templates: ProductTemplate[] = [];
  isLoading: boolean = false;

  constructor(private templateService: ProductTemplateService) {}

  ngOnInit(): void {
    this.loadTemplates();
  }

  loadTemplates(): void {
    this.isLoading = true;
    this.templateService.getProductTemplates().subscribe({
      next: (templates) => {
        this.templates = templates;
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading templates:', error);
        this.isLoading = false;
      }
    });
  }

  deleteTemplate(id: number): void {
    if (confirm('Are you sure you want to delete this template?')) {
      this.templateService.deleteProductTemplate(id).subscribe({
        next: () => {
          this.loadTemplates(); // Refresh the list
        },
        error: (error) => {
          console.error('Error deleting template:', error);
        }
      });
    }
  }
}