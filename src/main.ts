import { connect } from '@allthespaces/portal';
import { Engine } from './engine/engine.ts';
import { makeInstallable, standaloneTier } from './installable.ts';
import './style.css';

makeInstallable();
const portal = await connect({ save: { version: 1 } });
// On its own, the SDK's stand-in calls every device 'high'; choose as All the Spaces would.
if (portal.standalone) (portal as { tier: typeof portal.tier }).tier = standaloneTier();
const engine = new Engine(portal);
await engine.boot();
