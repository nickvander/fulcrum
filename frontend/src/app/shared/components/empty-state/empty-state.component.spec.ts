import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EmptyStateComponent } from './empty-state.component';

describe('EmptyStateComponent', () => {
  let fixture: ComponentFixture<EmptyStateComponent>;
  let component: EmptyStateComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EmptyStateComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(EmptyStateComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('defaults to the neutral tone: Material icon, no wedge', () => {
    component.icon = 'inventory_2';
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('.empty-state--peer')).toBeNull();
    expect(root.querySelector('.empty-wedge')).toBeNull();
    expect(root.querySelector('mat-icon')).not.toBeNull();
  });

  it('peer tone renders the pivot-wedge glyph + peer copy (no Material icon)', () => {
    component.tone = 'peer';
    component.title = 'Aquí cae tu primera venta';
    component.description = 'Cuando entre un pedido, lo vas a ver aquí mismo.';
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('.empty-state--peer')).not.toBeNull();
    expect(root.querySelector('.empty-wedge')).not.toBeNull();
    // Wedge replaces the Material icon in peer tone.
    expect(root.querySelector('mat-icon')).toBeNull();
    expect(root.querySelector('h3')?.textContent).toContain('Aquí cae tu primera venta');
    expect(root.querySelector('p')?.textContent).toContain('Cuando entre un pedido');
  });

  it('useWedge override forces the wedge on even in the neutral tone', () => {
    component.tone = 'neutral';
    component.useWedge = true;
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).querySelector('.empty-wedge')).not.toBeNull();
  });

  it('useWedge=false suppresses the wedge even in the peer tone (icon fallback)', () => {
    component.tone = 'peer';
    component.useWedge = false;
    component.icon = 'forum';
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('.empty-wedge')).toBeNull();
    expect(root.querySelector('mat-icon')).not.toBeNull();
  });
});
