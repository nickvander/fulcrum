import { Injectable } from '@angular/core';
import { Observable, from, throwError } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class HardwareService {
  constructor() {}

  /**
   * Requests access to the user's camera and returns a MediaStream.
   * @returns An Observable that emits the MediaStream.
   */
  getCameraStream(): Observable<MediaStream> {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return throwError(
        () => new Error('Browser API navigator.mediaDevices.getUserMedia not available')
      );
    }

    return from(
      navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }, // Prefer the rear camera
      })
    );
  }

  /**
   * Captures a still image from a MediaStream and returns it as a Blob.
   * @param stream The MediaStream from the camera.
   * @returns A Promise that resolves with the image Blob.
   */
  captureImage(stream: MediaStream): Promise<Blob> {
    return new Promise((resolve, reject) => {
      const track = stream.getVideoTracks()[0];
      if (!track) {
        return reject('No video track found in the stream.');
      }

      if ('ImageCapture' in window) {
        const imageCapture = new (window as any).ImageCapture(track);
        if (!imageCapture) {
          return reject('ImageCapture API not available.');
        }

        imageCapture
          .takePhoto()
          .then((blob: Blob) => {
            resolve(blob);
          })
          .catch((error: any) => {
            reject(error);
          });
      } else {
        // Fallback for browsers that don't support ImageCapture
        const video = document.createElement('video');
        video.srcObject = stream;
        video.play();

        video.addEventListener('loadeddata', () => {
          const canvas = document.createElement('canvas');
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          const context = canvas.getContext('2d');
          if (context) {
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            canvas.toBlob(blob => {
              if (blob) {
                resolve(blob);
              } else {
                reject('Canvas to Blob conversion failed.');
              }
            }, 'image/jpeg');
          } else {
            reject('Could not get canvas context.');
          }
        });
      }
    });
  }
}
