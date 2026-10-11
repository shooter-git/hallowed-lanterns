import { connect } from '@allthespaces/portal';
import { Engine } from './engine/engine.ts';
import './style.css';

const portal = await connect({ save: { version: 1 } });
const engine = new Engine(portal);
await engine.boot();
