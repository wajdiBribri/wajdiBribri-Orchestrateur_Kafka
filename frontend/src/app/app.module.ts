import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { AppComponent } from './app.component';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import { HttpClientModule } from '@angular/common/http';
cytoscape.use(dagre);

@NgModule({
  declarations: [
    AppComponent
  ],
  imports: [
    BrowserModule,HttpClientModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
