import './app.css';
import './styles/admin.css';
import './styles/stats.css';
import './styles/imports.css';
import './styles/editor.css';
import App from './App.svelte';
import { mount } from 'svelte';

const app = mount(App, {
  target: document.getElementById('app')!
});

export default app;
