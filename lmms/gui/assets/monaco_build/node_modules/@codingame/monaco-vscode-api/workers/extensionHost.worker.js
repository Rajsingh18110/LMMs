import { create } from '../vscode/src/vs/workbench/api/worker/extensionHostWorker.js';
const messageHandler = create();
globalThis.onmessage = (e) => messageHandler.onmessage(e.data);
