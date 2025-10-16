import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'orderBy',
  standalone: true
})
export class OrderByPipe implements PipeTransform {
  transform(array: any[], field: string, reverse: boolean = false): any[] {
    if (!array || !field) {
      return array;
    }

    const sortedArray = [...array].sort((a, b) => {
      const valueA = a[field];
      const valueB = b[field];

      if (valueA < valueB) {
        return reverse ? 1 : -1;
      } else if (valueA > valueB) {
        return reverse ? -1 : 1;
      } else {
        return 0;
      }
    });

    return sortedArray;
  }
}