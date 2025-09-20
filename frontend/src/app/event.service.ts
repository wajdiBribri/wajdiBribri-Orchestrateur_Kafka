import { Injectable, NgZone } from '@angular/core';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class EventService {
  constructor(private zone: NgZone) {}

  getEvents(): Observable<any> {
    return new Observable(observer => {
      const eventSource = new EventSource('/events/stream');

      eventSource.onmessage = (event) => {
        // Angular zone pour mettre à jour la vue
        this.zone.run(() => {
          console.log('Event reçu:', event.data);
          observer.next(JSON.parse(event.data));
        });
      };

      eventSource.onerror = (error) => {
        console.error('EventSource failed:', error);
        eventSource.close();
        observer.complete();
      };

      // Cleanup si l'observable est unsubscribed
      return () => eventSource.close();
    });
  }
}
