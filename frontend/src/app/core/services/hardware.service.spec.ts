import { TestBed } from '@angular/core/testing';
import { HardwareService } from './hardware.service';
import { firstValueFrom } from 'rxjs';

describe('HardwareService', () => {
  let service: HardwareService;
  let getUserMediaSpy: jasmine.Spy;
  let mediaDevicesPropertyDescriptor: PropertyDescriptor | undefined;

  beforeEach(() => {
    // Store the original property descriptor
    mediaDevicesPropertyDescriptor = Object.getOwnPropertyDescriptor(
      navigator,
      'mediaDevices'
    );

    // Create a spy and a mock object
    getUserMediaSpy = jasmine.createSpy('getUserMediaSpy');
    const mockMediaDevices = {
      getUserMedia: getUserMediaSpy,
    };

    // Make the property writable and set the mock
    Object.defineProperty(navigator, 'mediaDevices', {
      writable: true,
      value: mockMediaDevices,
    });

    TestBed.configureTestingModule({});
    service = TestBed.inject(HardwareService);
  });

  afterEach(() => {
    // Restore the original property descriptor
    if (mediaDevicesPropertyDescriptor) {
      Object.defineProperty(
        navigator,
        'mediaDevices',
        mediaDevicesPropertyDescriptor
      );
    }
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

    await expectAsync(
      firstValueFrom(service.getCameraStream())
    ).toBeRejectedWith(mockError);
  });
});
