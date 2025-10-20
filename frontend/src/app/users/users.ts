import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-users',
  standalone: true,
  imports: [RouterOutlet],
  templateUrl: './users.html',
  styleUrl: './users.scss'
})
export class Users {

}
