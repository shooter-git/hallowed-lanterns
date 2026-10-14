import { connect } from '@allthespaces/portal';
import { Engine } from './engine/engine.ts';
import { makeInstallable } from './installable.ts';
import './style.css';

makeInstallable();
const portal = await connect({ save: { version: 1 } });
const engine = new Engine(portal);
await engine.boot();
