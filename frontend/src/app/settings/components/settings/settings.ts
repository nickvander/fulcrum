import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';

@Component({
  selector: 'app-settings',
  templateUrl: './settings.html',
  styleUrl: './settings.scss'
})
export class Settings implements OnInit {
  settingsForm: FormGroup;

  constructor(private fb: FormBuilder) {
    this.settingsForm = this.fb.group({
      ai_provider: ['', Validators.required],
      ai_api_key: ['', Validators.required],
      theme: ['light', Validators.required]
    });
  }

  ngOnInit(): void {
    // TODO: Load initial settings from a service
  }

  onSubmit(): void {
    if (this.settingsForm.valid) {
      console.log('Settings saved:', this.settingsForm.value);
      // TODO: Call a service to save the settings
    }
  }
}
