import { TestBed } from '@angular/core/testing';
import { HardwareService } from './hardware.service';

describe('HardwareService', () => {
  let service: HardwareService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(HardwareService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should request camera stream', (done) => {
    // Mock the browser API
    const mockStream = {} as MediaStream;
    const getUserMediaSpy = spyOn(navigator.mediaDevices, 'getUserMedia').and.returnValue(
      Promise.resolve(mockStream)
    );

    service.getCameraStream().subscribe((stream) => {
      expect(stream).toBe(mockStream);
      expect(getUserMediaSpy).toHaveBeenCalledWith({
        video: { facingMode: 'environment' },
      });
      done();
    });
  });

  it('should handle camera access denial', (done) => {
    const mockError = new Error('Permission denied');
    spyOn(navigator.mediaDevices, 'getUserMedia').and.returnValue(
      Promise.reject(mockError)
    );

    service.getCameraStream().subscribe({
      next: () => fail('should have failed'),
      error: (err) => {
        expect(err).toBe(mockError);
        done();
      },
    });
  });
});
