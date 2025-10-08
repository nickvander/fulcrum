import { TestBed } from '@angular/core/testing';
import { HardwareService } from './hardware.service';
import { firstValueFrom } from 'rxjs';

describe('HardwareService', () => {
  let service: HardwareService;
  let getUserMediaSpy: jasmine.Spy;
  let originalMediaDevices: any;

  beforeEach(() => {
    // Store the original object so we can restore it
    originalMediaDevices = navigator.mediaDevices;

    // Create a spy and build a completely new mock object
    getUserMediaSpy = jasmine.createSpy('getUserMediaSpy');
    (navigator as any).mediaDevices = {
      getUserMedia: getUserMediaSpy
    };

    TestBed.configureTestingModule({});
    service = TestBed.inject(HardwareService);
  });

  afterEach(() => {
    // Restore the original object after each test
    (navigator as any).mediaDevices = originalMediaDevices;
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should request camera stream', async () => {
    const mockStream = {} as MediaStream;
    getUserMediaSpy.and.returnValue(Promise.resolve(mockStream));

    const stream = await firstValueFrom(service.getCameraStream());

    expect(stream).toBe(mockStream);
    expect(getUserMediaSpy).toHaveBeenCalledWith({
      video: { facingMode: 'environment' },
    });
  });

  it('should handle camera access denial', async () => {
    const mockError = new Error('Permission denied');
    getUserMediaSpy.and.returnValue(Promise.reject(mockError));

    await expectAsync(firstValueFrom(service.getCameraStream())).toBeRejectedWith(mockError);
  });
});
