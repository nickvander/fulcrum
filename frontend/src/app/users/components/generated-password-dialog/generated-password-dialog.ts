import { Component, Inject } from '@angular/core';

import { MatButtonModule } from '@angular/material/button';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-generated-password-dialog',
  templateUrl: './generated-password-dialog.html',
  styleUrls: ['./generated-password-dialog.scss'],
  standalone: true,
  imports: [
    MatDialogModule,
    MatButtonModule,
    MatIconModule
],
})
export class GeneratedPasswordDialog {
  constructor(
    public dialogRef: MatDialogRef<GeneratedPasswordDialog>,
    @Inject(MAT_DIALOG_DATA) public data: { password: string, userEmail: string }
  ) {}

  onCopyPassword(): void {
    navigator.clipboard.writeText(this.data.password).then(() => {
      // Optional: show a temporary message that the password was copied
    });
  }

  onOk(): void {
    this.dialogRef.close();
  }
}