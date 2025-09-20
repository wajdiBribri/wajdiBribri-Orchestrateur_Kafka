import { Component, NgZone, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import cytoscape from 'cytoscape';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  events: any[] = [];
  cy: any;

  constructor(private http: HttpClient, private zone: NgZone) {}

  ngOnInit(): void {
    //this.listenEvents();
  }

  startOrchestration() {
    this.http.post('http://localhost:8000/orchestrate', {}).subscribe((res: any) => {
      this.listenEvents()
      this.loadGraph();
    });
  }

  listenEvents() {
    const eventSource = new EventSource('http://localhost:8000/events/stream');
    eventSource.onmessage = (event) => {
      this.zone.run(() => {
        this.events.unshift(JSON.parse(event.data));
      });
    };
    eventSource.onerror = (err) => {
      console.error('EventSource failed', err);
      eventSource.close();
    };
  }

  loadGraph() {
    this.http.get('http://localhost:8000/dag/json').subscribe((data: any) => {
      // initialisation Cytoscape
      this.cy = cytoscape({
        container: document.getElementById('graph'),
        elements: [
          ...data.nodes.map((n: { id: { toString: () => any; }; label: any; }) => ({ data: { id: n.id.toString(), label: n.label } })),
          ...data.edges.map((e: { source: { toString: () => any; }; target: { toString: () => any; }; }) => ({ data: { source: e.source.toString(), target: e.target.toString() } }))
        ],
        style: [
          {
            selector: 'node',
            style: {
              'content': 'data(label)',
              'text-valign': 'center',
              'color': '#fff',
              'background-color': '#0074D9',
              'width': 'label',
              'height': 'label',
              'padding': '10px'
            }
          },
          {
            selector: 'edge',
            style: {
              'width': 2,
              'line-color': '#ccc',
              'target-arrow-color': '#ccc',
              'target-arrow-shape': 'triangle'
            }
          }
        ],
        layout: { name: 'dagre' } // tu peux utiliser 'breadthfirst' ou 'cose'
      });
    });
  }
}
